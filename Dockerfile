# MCP server image for okf-kit.
#
# Runs `okf serve-mcp` over stdio, exposing an OKF knowledge bundle to MCP
# clients (Claude Code, Cursor, …) via the tools: list_bundles,
# list_directory, read_concept, search_bundle.
#
# It bakes in the community `rust-book` bundle so the server has real content
# to serve out of the box (and so registry/Glama introspection passes). Swap
# the bundle by overriding the command, e.g.:
#   docker run -i --rm <image> okf serve-mcp <other-bundle>
# or serve every bundle you've pulled into the image with `okf serve-mcp --all`.
#
# Build:  docker build -t okf-kit-mcp .
# Run:    docker run -i --rm okf-kit-mcp        # speaks MCP over stdio
FROM python:3.12-slim

RUN pip install --no-cache-dir "okf-kit[mcp]"

# Pull a real bundle into the image (~/.okf/bundles/rust-book).
RUN okf get rust-book --yes

ENTRYPOINT ["okf", "serve-mcp", "rust-book"]
