"""Score a labelled call set with Gemini, saving a resumable run separately.

The default is a dry-run. --run makes Gemini requests, so it must be explicit.
Runs are keyed by the input data, model, and scoring versions; the web demo's
simulated fixture is never overwritten.
"""
import argparse, asyncio, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from dotenv import load_dotenv
load_dotenv(ROOT/'backend'/'.env')
from fastapi import HTTPException
from scoring import assess, VERSION, POLICY_VERSION

def load_dataset(source: Path):
    """Load the legacy JSON pilot or a JSONL simulated corpus."""
    if source.suffix == '.jsonl':
        manifest_path = source.with_suffix('.manifest.json')
        if not manifest_path.exists():
            raise SystemExit(f'Missing manifest for {source.name}.')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        records = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
        return dict(version=manifest['version'], provenance=manifest['provenance'], records=records)
    return json.loads(source.read_text(encoding='utf-8'))


def output_path(source: Path, requested: str | None) -> Path:
    if requested:
        path = Path(requested)
        return path if path.is_absolute() else ROOT / path
    return ROOT / 'evaluation' / 'runs' / f'{source.stem}-all.json'

def metrics(rows):
    binary=[r for r in rows if r['label'] is not None]
    positives=sum(r['label']==1 for r in binary)
    negatives=len(binary)-positives
    def divide(a,b): return a/b if b else None
    tp=sum(r['label']==1 and r['assessment']['decision']=='BLOCK' for r in binary)
    fp=sum(r['label']==0 and r['assessment']['decision']=='BLOCK' for r in binary)
    fn=positives-tp; tn=negatives-fp
    curves=[]
    if positives and negatives:
        for threshold in [1.000001]+sorted({r['assessment']['risk_score'] for r in binary},reverse=True):
            p=sum(r['label']==1 and r['assessment']['risk_score']>=threshold for r in binary)
            n=sum(r['label']==0 and r['assessment']['risk_score']>=threshold for r in binary)
            curves.append(dict(threshold=threshold,tpr=p/positives,fpr=n/negatives,precision=divide(p,p+n)))
    latency=sorted(r['assessment']['latency_ms'] for r in rows)
    def percentile(q):
        if not latency:return None
        i=(len(latency)-1)*q; lo=int(i); hi=min(lo+1,len(latency)-1)
        return latency[lo]+(latency[hi]-latency[lo])*(i-lo)
    return dict(n=len(rows),binary_n=len(binary),positives=positives,negatives=negatives,
        confusion=dict(tp=tp,fp=fp,fn=fn,tn=tn),precision=divide(tp,tp+fp),recall=divide(tp,positives),false_positive_rate=divide(fp,negatives),
        decision_accuracy=divide(sum(r['assessment']['decision']==r['expected_decision'] for r in rows),len(rows)),
        p50_ms=percentile(.5),p95_ms=percentile(.95),curves=curves)

async def run(args):
    source=Path(args.dataset)
    if not source.is_absolute(): source=ROOT/source
    if not source.exists(): raise SystemExit(f'Dataset not found: {source}')
    dataset=load_dataset(source)
    signature=hashlib.sha256(source.read_bytes()).hexdigest()
    identity=dict(dataset_hash=signature,dataset_version=dataset['version'],prompt_version=VERSION,policy_version=POLICY_VERSION,model=os.getenv('GEMINI_MODEL','gemini-3.8-flash'))
    path=output_path(source,args.output)
    result=json.loads(path.read_text()) if path.exists() else dict(**identity,records=[],errors=[])
    if any(result.get(k)!=v for k,v in identity.items()):
        raise SystemExit(f'Existing run at {path} uses different data or scoring settings. Choose a different --output path.')
    done={r['id'] for r in result['records']}
    pending=[r for r in dataset['records'] if r['id'] not in done and (args.split=='all' or r['split']==args.split)]
    if args.dry_run:
        selected=[r for r in dataset['records'] if args.split=='all' or r['split']==args.split]
        print(json.dumps(dict(dataset=source.name,result_file=str(path),selected=len(selected),completed=len(done),pending=len(pending),next_ids=[r['id'] for r in pending[:args.limit]])));return
    def save(status):
        result.update(
            status=status,
            updated_at=datetime.now(timezone.utc).isoformat(),
            provenance=dataset['provenance'],
            source_dataset=source.name,
            selected_split=args.split,
            selected_total=len([r for r in dataset['records'] if args.split=='all' or r['split']==args.split]),
            summaries=dict(
                all=metrics(result['records']),
                development=metrics([r for r in result['records'] if r['split']=='development']),
                validation=metrics([r for r in result['records'] if r['split']=='validation']),
                held_out=metrics([r for r in result['records'] if r['split']=='held_out']),
            ),
        )
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(result,indent=2),encoding='utf-8');temp.replace(path)
    for case in pending[:args.limit]:
        try:
            assessment=await assess(case['conversation'])
            result['records'].append(dict(**case,assessment=assessment.model_dump()))
            save('partial');print(case['id'],assessment.decision,flush=True)
        except HTTPException as exc:
            result['errors'].append(dict(id=case['id'],status=exc.status_code,time=datetime.now(timezone.utc).isoformat()))
            save('quota_exhausted' if exc.status_code==429 else 'provider_error')
            print('Stopped after provider error:',exc.status_code);return
        await asyncio.sleep(args.interval)
    selected_total=len([r for r in dataset['records'] if args.split=='all' or r['split']==args.split])
    selected_done=len([r for r in result['records'] if args.split=='all' or r['split']==args.split])
    save('complete' if selected_done==selected_total else 'partial')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true',help='Make Gemini calls and write recorded evaluation results.')
    parser.add_argument('--dry-run',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--limit',type=int,default=4);parser.add_argument('--interval',type=float,default=15)
    parser.add_argument('--split',choices=['development','held_out','all'],default='development')
    parser.add_argument('--dataset',default='evaluation/cases.json',help='JSON or JSONL labelled call set, relative to repository root.')
    parser.add_argument('--output',help='Run result JSON path. Defaults under evaluation/runs/.')
    args=parser.parse_args()
    if args.limit<1 or args.interval<0:parser.error('limit must be positive and interval nonnegative')
    args.dry_run=not args.run
    asyncio.run(run(args))
