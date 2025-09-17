#!/usr/bin/env python3
"""
MovieLens Metadata Loader for OpenSearch
Loads sample movie metadata into the sts-movielens-metadata-index
"""

import os
import json
import sys
import time
from typing import Dict, List, Any
from pathlib import Path
from dotenv import load_dotenv

# OpenSearch imports
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import OpenSearchException, RequestError, TransportError
import urllib3

# Load environment variables
load_dotenv()


class OpenSearchConfig:
    """OpenSearch configuration"""
    def __init__(self):
        self.host = os.getenv("OPENSEARCH_HOST", "localhost")
        self.port = int(os.getenv("OPENSEARCH_PORT", "9200"))
        self.username = os.getenv("OPENSEARCH_USERNAME")
        self.password = os.getenv("OPENSEARCH_PASSWORD")
        self.use_ssl = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"
        self.ssl_verify = os.getenv("OPENSEARCH_SSL_VERIFY", "false").lower() == "true"
        self.ssl_show_warn = os.getenv("OPENSEARCH_SSL_SHOW_WARN", "false").lower() == "true"
        self.timeout = int(os.getenv("OPENSEARCH_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("OPENSEARCH_MAX_RETRIES", "3"))

        if not self.username or not self.password:
            raise ValueError("OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD must be set")


class MovieLensLoader:
    """Loads MovieLens metadata into OpenSearch"""

    def __init__(self, config: OpenSearchConfig):
        self.config = config
        self.client = self._create_client()
        self.index_name = "sts-movielens-metadata-index"

    def _create_client(self) -> OpenSearch:
        """Create OpenSearch client"""
        if not self.config.ssl_show_warn:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Parse host URL if it includes protocol
        host = self.config.host
        if host.startswith('https://'):
            host = host[8:]
            use_ssl = True
        elif host.startswith('http://'):
            host = host[7:]
            use_ssl = False
        else:
            use_ssl = self.config.use_ssl

        return OpenSearch(
            hosts=[{'host': host, 'port': self.config.port}],
            http_auth=(self.config.username, self.config.password),
            use_ssl=use_ssl,
            verify_certs=self.config.ssl_verify,
            ssl_show_warn=self.config.ssl_show_warn,
            connection_class=RequestsHttpConnection,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_on_timeout=True
        )

    def test_connection(self) -> bool:
        """Test connection to OpenSearch"""
        try:
            info = self.client.info()
            health = self.client.cluster.health()
            print(f"✅ Connected to OpenSearch cluster: {info.get('cluster_name')}")
            print(f"   Version: {info.get('version', {}).get('number')}")
            print(f"   Health: {health.get('status')}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to OpenSearch: {e}")
            return False

    def create_index(self) -> bool:
        """Create the MovieLens metadata index with appropriate mapping"""
        try:
            # Check if index already exists
            if self.client.indices.exists(index=self.index_name):
                print(f"⚠️  Index '{self.index_name}' already exists")
                response = input("Do you want to delete and recreate it? (y/N): ")
                if response.lower() == 'y':
                    self.client.indices.delete(index=self.index_name)
                    print(f"🗑️  Deleted existing index '{self.index_name}'")
                else:
                    return True

            # Define index mapping optimized for movie metadata
            mapping = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "analysis": {
                        "analyzer": {
                            "movie_analyzer": {
                                "tokenizer": "standard",
                                "filter": ["lowercase", "stop"]
                            }
                        }
                    }
                },
                "mappings": {
                    "properties": {
                        "title": {
                            "type": "text",
                            "analyzer": "movie_analyzer",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "directedBy": {
                            "type": "text",
                            "analyzer": "movie_analyzer",
                            "fields": {
                                "keyword": {
                                    "type": "keyword"
                                }
                            }
                        },
                        "starring": {
                            "type": "text",
                            "analyzer": "movie_analyzer"
                        },
                        "dateAdded": {
                            "type": "date",
                            "format": "yyyy-MM-dd'T'HH:mm:ss||yyyy-MM-dd||epoch_millis"
                        },
                        "avgRating": {
                            "type": "float"
                        },
                        "imdbId": {
                            "type": "keyword"
                        },
                        "item_id": {
                            "type": "integer"
                        },
                        "year": {
                            "type": "integer"
                        },
                        "genre": {
                            "type": "keyword"
                        }
                    }
                }
            }

            self.client.indices.create(index=self.index_name, body=mapping)
            print(f"✅ Created index '{self.index_name}' with optimized mapping")
            return True

        except RequestError as e:
            print(f"❌ Failed to create index: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error creating index: {e}")
            return False

    def load_metadata(self, file_path: str) -> bool:
        """Load metadata from JSON file"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return False

            print(f"📖 Loading metadata from: {file_path}")

            documents = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        doc = json.loads(line.strip())

                        # Extract year from title if present
                        title = doc.get('title', '')
                        year = None
                        if title and '(' in title and ')' in title:
                            year_match = title.split('(')[-1].split(')')[0]
                            try:
                                year = int(year_match)
                                doc['year'] = year
                            except ValueError:
                                pass

                        documents.append(doc)

                        if line_num % 100 == 0:
                            print(f"   Loaded {line_num} documents...")

                    except json.JSONDecodeError as e:
                        print(f"⚠️  Skipping invalid JSON on line {line_num}: {e}")
                        continue

            print(f"📊 Total documents loaded: {len(documents)}")
            return self._bulk_index(documents)

        except Exception as e:
            print(f"❌ Error loading metadata: {e}")
            return False

    def _bulk_index(self, documents: List[Dict[str, Any]]) -> bool:
        """Bulk index documents with batching and backoff"""
        try:
            total_docs = len(documents)
            batch_size = 500  # Smaller batch size to avoid rate limits
            successful_docs = 0
            failed_docs = 0

            print(f"🚀 Bulk indexing {total_docs} documents in batches of {batch_size}...")

            # Process documents in batches
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (total_docs + batch_size - 1) // batch_size

                print(f"   Processing batch {batch_num}/{total_batches} ({len(batch)} docs)...")

                # Retry logic for each batch
                max_retries = 3
                retry_delay = 0.1

                for attempt in range(max_retries):
                    try:
                        # Prepare bulk operations for this batch
                        bulk_body = []
                        for doc in batch:
                            doc_id = doc.get('item_id')
                            bulk_body.append({
                                "index": {
                                    "_index": self.index_name,
                                    "_id": doc_id
                                }
                            })
                            bulk_body.append(doc)

                        # Perform bulk operation
                        response = self.client.bulk(body=bulk_body, refresh=False)

                        # Check for errors in this batch
                        batch_errors = 0
                        if response.get('errors'):
                            for item in response.get('items', []):
                                if 'index' in item and item['index'].get('error'):
                                    batch_errors += 1
                                    if batch_errors <= 3:  # Show first 3 errors per batch
                                        error = item['index']['error']
                                        print(f"     Error: {error.get('reason', 'Unknown error')}")

                        batch_success = len(batch) - batch_errors
                        successful_docs += batch_success
                        failed_docs += batch_errors

                        if batch_errors > 0:
                            print(f"     Batch completed: {batch_success} success, {batch_errors} errors")
                        else:
                            print(f"     Batch completed: {batch_success} documents indexed")

                        # Break out of retry loop on success
                        break

                    except TransportError as e:
                        if e.status_code == 429:  # Too Many Requests
                            if attempt < max_retries - 1:
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                                print(f"     Rate limited, waiting {wait_time:.1f}s before retry {attempt + 2}/{max_retries}...")
                                time.sleep(wait_time)
                                continue
                            else:
                                print(f"     ❌ Batch failed after {max_retries} retries: {e}")
                                failed_docs += len(batch)
                                break
                        else:
                            raise  # Re-raise non-429 errors

                    except Exception as e:
                        print(f"     ❌ Batch failed: {e}")
                        failed_docs += len(batch)
                        break

                # Small delay between batches to avoid overwhelming the cluster
                time.sleep(0.1)

            # Final refresh to make documents searchable
            try:
                self.client.indices.refresh(index=self.index_name)
                print(f"🔄 Index refreshed")
            except Exception as e:
                print(f"⚠️  Warning: Failed to refresh index: {e}")

            # Summary
            print(f"\n📊 Bulk indexing summary:")
            print(f"   ✅ Successfully indexed: {successful_docs} documents")
            if failed_docs > 0:
                print(f"   ❌ Failed to index: {failed_docs} documents")
                print(f"   📈 Success rate: {(successful_docs/total_docs)*100:.1f}%")
            else:
                print(f"   🎉 All documents indexed successfully!")

            return successful_docs > 0

        except Exception as e:
            print(f"❌ Bulk indexing failed: {e}")
            return False

    def verify_data(self) -> bool:
        """Verify that data was loaded correctly"""
        try:
            # Get index stats
            stats = self.client.indices.stats(index=self.index_name)
            doc_count = stats['indices'][self.index_name]['total']['docs']['count']

            print(f"📈 Index '{self.index_name}' contains {doc_count} documents")

            # Sample a few documents
            search_response = self.client.search(
                index=self.index_name,
                body={
                    "query": {"match_all": {}},
                    "size": 3,
                    "sort": [{"avgRating": {"order": "desc"}}]
                }
            )

            print(f"🎬 Top rated movies sample:")
            for hit in search_response['hits']['hits']:
                doc = hit['_source']
                print(f"   - {doc.get('title')} ({doc.get('avgRating'):.2f})")

            return True

        except Exception as e:
            print(f"❌ Data verification failed: {e}")
            return False


def main():
    """Main execution function"""
    print("🎬 MovieLens Metadata Loader for OpenSearch")
    print("=" * 50)

    try:
        # Load configuration
        config = OpenSearchConfig()

        # Initialize loader
        loader = MovieLensLoader(config)

        # Test connection
        if not loader.test_connection():
            sys.exit(1)

        # Create index
        if not loader.create_index():
            sys.exit(1)

        # Find metadata file
        script_dir = Path(__file__).parent
        metadata_file = script_dir.parent / "sample_data" / "metadata.json"

        if not metadata_file.exists():
            print(f"❌ Metadata file not found: {metadata_file}")
            print("Expected location: ../sample_data/metadata.json")
            sys.exit(1)

        # Load data
        if not loader.load_metadata(str(metadata_file)):
            sys.exit(1)

        # Verify data
        if not loader.verify_data():
            sys.exit(1)

        print("\n✅ MovieLens metadata loading completed successfully!")
        print(f"🔍 You can now search the '{loader.index_name}' index")

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("Please set OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD environment variables")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()