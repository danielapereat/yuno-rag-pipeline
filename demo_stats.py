#!/usr/bin/env python3.11
"""
Demo script to show database statistics.
"""

from pymongo import MongoClient
from config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
collection = client[MONGODB_DATABASE][MONGODB_COLLECTION]

# Print statistics
print('='*60)
print('📊 DATABASE STATISTICS')
print('='*60)
print(f'Total documents: {collection.count_documents({}):,}')
print(f'Jira tickets: {collection.count_documents({"metadata.document_type": "jira"})}')
print(f'Confluence docs: {collection.count_documents({"metadata.document_type": "confluence"})}')
print(f'TST12 tickets: {collection.count_documents({"metadata.source_id": {"$regex": "^TST12"}})}')
print('='*60)

# Show team breakdown
print('\nTEAM BREAKDOWN:')
print('='*60)
teams = collection.distinct("metadata.team")
for team in sorted([t for t in teams if t]):
    count = collection.count_documents({"metadata.team": team})
    print(f'{team}: {count} tickets')
print('='*60)
