# Third-party notices

The packaged application includes the following third-party software. Their license texts are kept in `third_party/` and must remain with any redistributed source or binary bundle.

## Node.js

- Component: Node.js runtime
- Version bundled in the build: 24.21.0 win-x64
- Project: https://nodejs.org/
- License and bundled notices: [`third_party/node-LICENSE.txt`](third_party/node-LICENSE.txt)

The Node.js license file includes notices for the Node.js project and its bundled components. Keep the complete file when redistributing the EXE.

## jsonc-parser

- Component: `jsonc-parser`
- Version: 3.3.1
- Copyright: Microsoft Corporation
- Project: https://github.com/microsoft/node-jsonc-parser
- License: MIT
- License text: [`third_party/jsonc-parser-LICENSE.md`](third_party/jsonc-parser-LICENSE.md)

The application uses this package locally to parse JSONC while preserving comments and formatting. It does not send configuration contents to the package authors or to a network service.

## Distribution rule

Include this file and the complete `third_party/` directory in source archives and portable release ZIPs. Do not replace these notices with a shortened summary.
