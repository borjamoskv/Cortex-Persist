import sqlite3
import sqlite_vec


def test_load():
    conn = sqlite3.connect(":memory:")
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        print("Successfully loaded sqlite-vec")

        cursor = conn.cursor()
        cursor.execute("SELECT vec_version()")
        print(f"vec_version: {cursor.fetchone()[0]}")
    except Exception as e:
        print(f"Failed to load sqlite-vec: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    test_load()
