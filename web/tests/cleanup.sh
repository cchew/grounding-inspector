#!/bin/bash
pkill -f "tsx src/server.ts" 2>/dev/null || true
rm -rf test-results/ playwright-report/
echo "Cleanup done"
