import os
import sqlite3
import json

# Try importing Google Cloud Spanner client library
try:
    from google.cloud import spanner
    HAS_SPANNER_SDK = True
except ImportError:
    HAS_SPANNER_SDK = False

class SpannerGraphClient:
    """
    Dual-Mode Spanner Graph Client.
    Connects to live Google Cloud Spanner if SPANNER_INSTANCE is configured,
    otherwise falls back to a local SQLite database (spanner_mock.db) with
    Cypher GQL query translation to keep executions self-contained.
    """
    def __init__(self, db_path: str = "spanner_mock.db"):
        self.db_path = db_path
        self.instance_id = os.getenv("SPANNER_INSTANCE")
        self.database_id = os.getenv("SPANNER_DATABASE", "bdd-db")
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        # Determine mode
        if HAS_SPANNER_SDK and self.instance_id and self.project_id:
            self.mode = "gcp"
            self.spanner_client = spanner.Client(project=self.project_id)
            self.instance = self.spanner_client.instance(self.instance_id)
            self.database = self.instance.database(self.database_id)
            print(f"Spanner Client initialized in GCP mode (Instance: {self.instance_id})")
        else:
            self.mode = "sqlite_mock"
            self._init_sqlite_db()
            print(f"Spanner Client initialized in Mock mode (SQLite: {self.db_path})")

    def _init_sqlite_db(self):
        """Initializes local SQLite database tables if not existing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables mapping our node and edge definitions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS UserStory (
            story_id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            embedding TEXT,
            verified_spec TEXT
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS GherkinStep (
            step_id TEXT PRIMARY KEY,
            step_type TEXT,
            text TEXT,
            embedding TEXT
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS RubyDefinition (
            definition_id TEXT PRIMARY KEY,
            expression TEXT,
            code_block TEXT,
            embedding TEXT
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS StoryImplementsStep (
            story_id TEXT,
            step_id TEXT,
            PRIMARY KEY (story_id, step_id),
            FOREIGN KEY (story_id) REFERENCES UserStory (story_id),
            FOREIGN KEY (step_id) REFERENCES GherkinStep (step_id)
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS StepBindsDefinition (
            step_id TEXT,
            definition_id TEXT,
            PRIMARY KEY (step_id, definition_id),
            FOREIGN KEY (step_id) REFERENCES GherkinStep (step_id),
            FOREIGN KEY (definition_id) REFERENCES RubyDefinition (definition_id)
        )""")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS StoryDependsOnStory (
            story_id TEXT,
            depends_on_story_id TEXT,
            PRIMARY KEY (story_id, depends_on_story_id),
            FOREIGN KEY (story_id) REFERENCES UserStory (story_id),
            FOREIGN KEY (depends_on_story_id) REFERENCES UserStory (story_id)
        )""")
        
        conn.commit()
        conn.close()

    def insert_node(self, label: str, node_id: str, properties: dict, embedding: list = None):
        """Inserts or replaces a node in the graph database."""
        # Map labels to their specific ID column names
        id_map = {
            "UserStory": "story_id",
            "GherkinStep": "step_id",
            "RubyDefinition": "definition_id"
        }
        id_col = id_map.get(label)
        if not id_col:
            raise ValueError(f"Unknown node label: {label}")

        if self.mode == "gcp":
            # GCP Cloud Spanner write transaction
            def write_transaction(transaction):
                columns = [k for k in properties.keys()] + [id_col]
                values = [v for v in properties.values()] + [node_id]
                if embedding:
                    columns.append("embedding")
                    values.append(embedding)
                transaction.insert_or_update(
                    table=label,
                    columns=columns,
                    values=[values]
                )
            self.database.run_in_transaction(write_transaction)
        else:
            # SQLite Mock write
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            
            # Construct dynamic query
            keys = [k for k in properties.keys()] + [id_col]
            vals = [v for v in properties.values()] + [node_id]
            placeholders = ",".join(["?"] * len(keys))
            
            if embedding:
                keys.append("embedding")
                vals.append(json.dumps(embedding))
                placeholders += ",?"
                
            query = f"INSERT OR REPLACE INTO {label} ({','.join(keys)}) VALUES ({placeholders})"
            cursor.execute(query, vals)
            conn.commit()
            conn.close()

    def insert_edge(self, label: str, source_id: str, destination_id: str):
        """Inserts an edge connecting two nodes in the graph database."""
        if label.upper() == "IMPLEMENTS":
            table = "StoryImplementsStep"
            cols = ["story_id", "step_id"]
        elif label.upper() == "BINDS":
            table = "StepBindsDefinition"
            cols = ["step_id", "definition_id"]
        elif label.upper() == "DEPENDS_ON":
            table = "StoryDependsOnStory"
            cols = ["story_id", "depends_on_story_id"]
        else:
            raise ValueError(f"Unknown edge label: {label}")
            
        if self.mode == "gcp":
            def write_transaction(transaction):
                transaction.insert_or_update(
                    table=table,
                    columns=cols,
                    values=[[source_id, destination_id]]
                )
            self.database.run_in_transaction(write_transaction)
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = f"INSERT OR REPLACE INTO {table} ({cols[0]}, {cols[1]}) VALUES (?, ?)"
            cursor.execute(query, (source_id, destination_id))
            conn.commit()
            conn.close()

    def execute_gql(self, query: str) -> list[dict]:
        """
        Executes a Graph Query Language (GQL) query.
        In SQLite mock mode, translates basic Cypher lookups to equivalent SQL JOINs.
        """
        if self.mode == "gcp":
            # Live Spanner GQL via SQL query interface
            results = []
            with self.database.snapshot() as snapshot:
                result_set = snapshot.execute_sql(query)
                for row in result_set:
                    row_dict = {}
                    for i, col in enumerate(result_set.fields):
                        row_dict[col.name] = row[i]
                    results.append(row_dict)
            return results
        else:
            # SQLite GQL translation
            # Handles: MATCH (s:UserStory)-[:IMPLEMENTS]->(g:GherkinStep) RETURN s.story_id, g.step_id
            query_clean = query.strip().upper()
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if "IMPLEMENTS" in query_clean:
                sql = """
                    SELECT s.story_id, s.title, s.description, g.step_id, g.step_type, g.text
                    FROM UserStory s
                    JOIN StoryImplementsStep e ON s.story_id = e.story_id
                    JOIN GherkinStep g ON e.step_id = g.step_id
                """
            elif "BINDS" in query_clean:
                sql = """
                    SELECT g.step_id, g.text, r.definition_id, r.expression, r.code_block
                    FROM GherkinStep g
                    JOIN StepBindsDefinition e ON g.step_id = e.step_id
                    JOIN RubyDefinition r ON e.definition_id = r.definition_id
                """
            elif "DEPENDS_ON" in query_clean:
                sql = """
                    SELECT s1.story_id AS story_id, s1.title AS story_title,
                           s2.story_id AS depends_on_id, s2.title AS depends_on_title
                    FROM UserStory s1
                    JOIN StoryDependsOnStory e ON s1.story_id = e.story_id
                    JOIN UserStory s2 ON e.depends_on_story_id = s2.story_id
                """
            else:
                # Default generic dump for fallback checks
                sql = "SELECT * FROM UserStory"
                
            cursor.execute(sql)
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
            
    def get_all_ruby_definitions(self) -> list[dict]:
        """Retrieves all registered Ruby step definition expressions."""
        if self.mode == "gcp":
            query = "SELECT definition_id, expression, code_block FROM RubyDefinition"
            return self.execute_gql(query)
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT definition_id, expression, code_block FROM RubyDefinition")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def update_user_story_spec(self, story_id: str, verified_spec: str):
        """Updates the verified Dafny specification code for a UserStory in the database."""
        if self.mode == "gcp":
            def write_transaction(transaction):
                transaction.insert_or_update(
                    table="UserStory",
                    columns=["story_id", "verified_spec"],
                    values=[[story_id, verified_spec]]
                )
            self.database.run_in_transaction(write_transaction)
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE UserStory SET verified_spec = ? WHERE story_id = ?",
                (verified_spec, story_id)
            )
            conn.commit()
            conn.close()

    def find_similar_verified_story(self, query_embedding: list[float], exclude_story_id: str) -> dict | None:
        """
        Performs vector search (cosine similarity) to find the most semantically
        similar User Story in the database that has a verified_spec.
        """
        if not query_embedding:
            return None
            
        if self.mode == "gcp":
            sql = """
                SELECT story_id, title, description, verified_spec,
                       COSINE_DISTANCE(embedding, @query_emb) AS distance
                FROM UserStory
                WHERE story_id != @exclude_id AND verified_spec IS NOT NULL
                ORDER BY distance ASC
                LIMIT 1
            """
            try:
                with self.database.snapshot() as snapshot:
                    params = {"query_emb": query_embedding, "exclude_id": exclude_story_id}
                    param_types = {
                        "query_emb": spanner.param_types.Array(spanner.param_types.FLOAT64),
                        "exclude_id": spanner.param_types.STRING
                    }
                    result_set = snapshot.execute_sql(sql, params=params, param_types=param_types)
                    for row in result_set:
                        return {
                            "story_id": row[0],
                            "title": row[1],
                            "description": row[2],
                            "verified_spec": row[3]
                        }
            except Exception as e:
                print(f"Warning: GCP Spanner vector search query failed ({e}).")
            return None
        else:
            # Local SQLite ANN search fallback: calculate cosine similarity manually
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT story_id, title, description, embedding, verified_spec FROM UserStory WHERE story_id != ? AND verified_spec IS NOT NULL",
                (exclude_story_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            best_match = None
            highest_similarity = -1.0
            
            import math
            def cosine_similarity(v1, v2):
                if len(v1) != len(v2):
                    return 0.0
                dot_product = sum(x * y for x, y in zip(v1, v2))
                norm_v1 = math.sqrt(sum(x * x for x in v1))
                norm_v2 = math.sqrt(sum(x * x for x in v2))
                if norm_v1 == 0.0 or norm_v2 == 0.0:
                    return 0.0
                return dot_product / (norm_v1 * norm_v2)
                
            for row in rows:
                if not row["embedding"]:
                    continue
                try:
                    emb = json.loads(row["embedding"])
                    sim = cosine_similarity(query_embedding, emb)
                    if sim > highest_similarity:
                        highest_similarity = sim
                        best_match = {
                            "story_id": row["story_id"],
                            "title": row["title"],
                            "description": row["description"],
                            "verified_spec": row["verified_spec"],
                            "similarity": sim
                        }
                except Exception:
                    continue
            return best_match

    def get_dependent_stories(self, story_id: str) -> list[dict]:
        """Traverses DEPENDS_ON edges to find all stories that depend on the current story."""
        if self.mode == "gcp":
            sql = """
                SELECT story_id, title
                FROM UserStory
                WHERE story_id IN (
                    SELECT story_id FROM StoryDependsOnStory WHERE depends_on_story_id = @story_id
                )
            """
            try:
                with self.database.snapshot() as snapshot:
                    params = {"story_id": story_id}
                    param_types = {"story_id": spanner.param_types.STRING}
                    result_set = snapshot.execute_sql(sql, params=params, param_types=param_types)
                    return [{"story_id": row[0], "title": row[1]} for row in result_set]
            except Exception as e:
                print(f"Warning: GCP Spanner dependency query failed ({e}).")
            return []
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT story_id, title FROM UserStory
                WHERE story_id IN (
                    SELECT story_id FROM StoryDependsOnStory WHERE depends_on_story_id = ?
                )
                """,
                (story_id,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [{"story_id": r["story_id"], "title": r["title"]} for r in rows]

    def find_closest_ruby_definition(self, query_embedding: list[float]) -> dict | None:
        """
        Executes a combined Vector Search (ANN) and GQL Traversal to find
        the closest matching Ruby step definition for a Gherkin step embedding.
        Traverses: (GherkinStep) -[:BINDS]-> (RubyDefinition)
        """
        if not query_embedding:
            return None
            
        if self.mode == "gcp":
            sql = """
                SELECT r.definition_id, r.expression, r.code_block,
                       COSINE_DISTANCE(g.embedding, @query_emb) AS distance
                FROM GherkinStep g
                JOIN StepBindsDefinition e ON g.step_id = e.step_id
                JOIN RubyDefinition r ON e.definition_id = r.definition_id
                ORDER BY distance ASC
                LIMIT 1
            """
            try:
                with self.database.snapshot() as snapshot:
                    params = {"query_emb": query_embedding}
                    param_types = {"query_emb": spanner.param_types.Array(spanner.param_types.FLOAT64)}
                    result_set = snapshot.execute_sql(sql, params=params, param_types=param_types)
                    for row in result_set:
                        return {
                            "definition_id": row[0],
                            "expression": row[1],
                            "code_block": row[2]
                        }
            except Exception as e:
                print(f"Warning: GCP Spanner combined Vector-GQL query failed ({e}).")
            return None
        else:
            # Local SQLite ANN search fallback: calculate cosine similarity manually
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.definition_id, r.expression, r.code_block, g.embedding
                FROM GherkinStep g
                JOIN StepBindsDefinition e ON g.step_id = e.step_id
                JOIN RubyDefinition r ON e.definition_id = r.definition_id
                """
            )
            rows = cursor.fetchall()
            conn.close()
            
            best_match = None
            highest_similarity = -1.0
            
            import math
            import json
            def cosine_similarity(v1, v2):
                if len(v1) != len(v2):
                    return 0.0
                dot_product = sum(x * y for x, y in zip(v1, v2))
                norm_v1 = math.sqrt(sum(x * x for x in v1))
                norm_v2 = math.sqrt(sum(x * x for x in v2))
                if norm_v1 == 0.0 or norm_v2 == 0.0:
                    return 0.0
                return dot_product / (norm_v1 * norm_v2)
                
            for row in rows:
                if not row["embedding"]:
                    continue
                try:
                    emb = json.loads(row["embedding"])
                    sim = cosine_similarity(query_embedding, emb)
                    if sim > highest_similarity:
                        highest_similarity = sim
                        best_match = {
                            "definition_id": row["definition_id"],
                            "expression": row["expression"],
                            "code_block": row["code_block"],
                            "similarity": sim
                        }
                except Exception:
                    continue
            return best_match

    def get_dependent_stories_recursive(self, story_id: str) -> list[dict]:
        """
        Executes a recursive graph traversal to construct a downstream impact map
        answering 'what breaks if I change this?'.
        Returns all direct and indirect (transitive) dependents.
        """
        if self.mode == "gcp":
            sql = """
                WITH RECURSIVE DependentChain AS (
                    SELECT story_id, depends_on_story_id, 1 AS depth
                    FROM StoryDependsOnStory
                    WHERE depends_on_story_id = @story_id
                    
                    UNION ALL
                    
                    SELECT s.story_id, s.depends_on_story_id, dc.depth + 1
                    FROM StoryDependsOnStory s
                    JOIN DependentChain dc ON s.depends_on_story_id = dc.story_id
                    WHERE dc.depth < 10
                )
                SELECT dc.story_id, u.title, dc.depth
                FROM DependentChain dc
                JOIN UserStory u ON dc.story_id = u.story_id
            """
            try:
                with self.database.snapshot() as snapshot:
                    params = {"story_id": story_id}
                    param_types = {"story_id": spanner.param_types.STRING}
                    result_set = snapshot.execute_sql(sql, params=params, param_types=param_types)
                    dependents = {}
                    for row in result_set:
                        dep_id = row[0]
                        if dep_id not in dependents or row[2] < dependents[dep_id]["depth"]:
                            dependents[dep_id] = {
                                "story_id": dep_id,
                                "title": row[1],
                                "depth": row[2]
                            }
                    return list(dependents.values())
            except Exception as e:
                print(f"Warning: GCP Spanner recursive dependency query failed ({e}).")
            return []
        else:
            # SQLite Mock recursive lookup (BFS)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            visited = {}
            queue = [(story_id, 0)]
            
            while queue:
                curr_id, depth = queue.pop(0)
                
                cursor.execute(
                    """
                    SELECT s.story_id, u.title
                    FROM StoryDependsOnStory s
                    JOIN UserStory u ON s.story_id = u.story_id
                    WHERE s.depends_on_story_id = ?
                    """,
                    (curr_id,)
                )
                rows = cursor.fetchall()
                for r in rows:
                    dep_id = r["story_id"]
                    if dep_id not in visited:
                        visited[dep_id] = {
                            "story_id": dep_id,
                            "title": r["title"],
                            "depth": depth + 1
                        }
                        queue.append((dep_id, depth + 1))
            conn.close()
            return list(visited.values())

    def find_matching_ruby_definition(self, step_text: str) -> dict | None:
        """
        Queries the Spanner/SQLite Graph to find an exact matching Ruby definition
        regex for the given Gherkin step text.
        """
        import re
        step_clean = re.sub(r'^\$?(\d+)', r'\1', step_text.strip())
        
        if self.mode == "gcp":
            sql = """
                SELECT definition_id, expression, code_block
                FROM RubyDefinition
            """
            try:
                with self.database.snapshot() as snapshot:
                    result_set = snapshot.execute_sql(sql)
                    for row in result_set:
                        expr = row[1]
                        try:
                            pattern = re.compile(expr)
                            if pattern.search(step_text) or pattern.search(step_clean):
                                return {
                                    "definition_id": row[0],
                                    "expression": row[1],
                                    "code_block": row[2]
                                }
                        except Exception:
                            continue
            except Exception as e:
                print(f"Warning: GCP Spanner match query failed ({e}).")
            return None
        else:
            # SQLite Mock matching query
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT definition_id, expression, code_block FROM RubyDefinition")
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                expr = row["expression"]
                try:
                    pattern = re.compile(expr)
                    if pattern.search(step_text) or pattern.search(step_clean):
                        return {
                            "definition_id": row["definition_id"],
                            "expression": row["expression"],
                            "code_block": row["code_block"]
                        }
                except Exception:
                    continue
            return None

    def get_all_gherkin_steps(self) -> list[dict]:
        """
        Retrieves all GherkinStep nodes from the Spanner/SQLite Graph.
        """
        if self.mode == "gcp":
            sql = "SELECT step_id, step_type, text FROM GherkinStep"
            try:
                with self.database.snapshot() as snapshot:
                    result_set = snapshot.execute_sql(sql)
                    return [{"step_id": row[0], "step_type": row[1], "text": row[2]} for row in result_set]
            except Exception as e:
                print(f"Warning: GCP Spanner get_all_gherkin_steps failed ({e}).")
            return []
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT step_id, step_type, text FROM GherkinStep")
            rows = cursor.fetchall()
            conn.close()
            return [{"step_id": r["step_id"], "step_type": r["step_type"], "text": r["text"]} for r in rows]

    def delete_node(self, label: str, node_id: str):
        """Deletes a node from the database by ID."""
        id_map = {
            "UserStory": "story_id",
            "GherkinStep": "step_id",
            "RubyDefinition": "definition_id"
        }
        id_col = id_map.get(label)
        if not id_col:
            raise ValueError(f"Unknown node label: {label}")

        if self.mode == "gcp":
            def write_transaction(transaction):
                transaction.delete(label, spanner.KeySet([[node_id]]))
            self.database.run_in_transaction(write_transaction)
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = f"DELETE FROM {label} WHERE {id_col} = ?"
            cursor.execute(query, (node_id,))
            conn.commit()
            conn.close()

    def auto_prune_orphans(self) -> list[str]:
        """
        Finds and deletes all RubyDefinition nodes that do not have
        any BINDS relationship edges pointing to them from a GherkinStep.
        Returns the list of pruned definition IDs.
        """
        if self.mode == "gcp":
            sql = """
                SELECT definition_id FROM RubyDefinition
                WHERE definition_id NOT IN (SELECT definition_id FROM StepBindsDefinition)
            """
            try:
                with self.database.snapshot() as snapshot:
                    result_set = snapshot.execute_sql(sql)
                    pruned_ids = [row[0] for row in result_set]
                for node_id in pruned_ids:
                    self.delete_node("RubyDefinition", node_id)
                return pruned_ids
            except Exception as e:
                print(f"Warning: GCP Spanner auto_prune_orphans failed ({e}).")
            return []
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT definition_id FROM RubyDefinition
                WHERE definition_id NOT IN (SELECT definition_id FROM StepBindsDefinition)
                """
            )
            pruned_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            for node_id in pruned_ids:
                self.delete_node("RubyDefinition", node_id)
            return pruned_ids
