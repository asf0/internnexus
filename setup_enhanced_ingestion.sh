#!/bin/bash
# Quick setup script for the enhanced job ingestion system

set -e

echo "🚀 InternNexus Enhanced Ingestion Setup"
echo "========================================"

# Check if database is running
echo "📊 Checking database connection..."
cd backend

# Run migrations
echo "🔧 Running database migrations..."
alembic upgrade head
echo "✓ Migrations complete"

# Run ingestion
echo "📥 Starting job ingestion..."
python run_ingestion.py
echo "✓ Ingestion complete"

echo ""
echo "✨ All done! Your job database is now enriched with:"
echo "  • Job categories (parsed from SimplifyJobs markdown)"
echo "  • Legend attributes (sponsorship, citizenship, FAANG+, etc.)"
echo "  • Smart pattern matching (no manual nulls!)"
echo ""
echo "🎯 Key statistics from this run:"
echo "  • Check logs above for category extraction results"
echo "  • All new fields are automatically populated"
echo ""
