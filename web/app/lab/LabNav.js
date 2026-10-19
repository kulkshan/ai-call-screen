'use client';

import Link from 'next/link';
import styles from './LabNav.module.css';

const STATIC_DEMO=process.env.NEXT_PUBLIC_STATIC_DEMO==='1';

export default function LabNav({active = 'overview'}) {
  return <nav className={styles.nav} aria-label="Call Screen Lab">
    <Link className={styles.brand} href="/lab">
      <span className={styles.mark} aria-hidden="true"><i/><i/></span>
      <span>Call Screen Lab</span>
    </Link>
    <div className={styles.links}>{active==='live'
      ? <Link href="/lab">Back to case study</Link>
      : <Link href={STATIC_DEMO?'/' :'/?mode=live'}>{STATIC_DEMO?'Run guided demo':'Try a live call'}</Link>}
    </div>
  </nav>;
}
