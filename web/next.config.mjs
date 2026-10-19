const pages = process.env.GITHUB_ACTIONS === 'true';
const basePath = pages ? '/ai-call-screen' : '';

export default {
  output: 'export',
  trailingSlash: true,
  basePath,
  assetPrefix: basePath,
};
