import subprocess
result = subprocess.run(["pytest", "-q", "tests/test_api.py::TestAuth::test_good_key_accepted", "-x", "-v", "--tb=short"], capture_output=True, text=True)
print(result.stdout)
