"""Quick sanity tests for the layout converter."""
from layout import convert_text

tests = [
    # (input, expected_output, description)
    ("akuo", "שלום", "English keys → Hebrew 'shalom'"),
    ("שלום", "akuo", "Hebrew 'shalom' → English keys"),
    ("hello", "יקךךם", "English 'hello' → Hebrew layout chars"),
    ("יקךךם", "hello", "Hebrew layout chars → English 'hello'"),
]

# Round-trip tests: convert twice should give back original
round_trips = ["vsrgev", "akuo", "hello"]

passed = 0
for inp, expected, desc in tests:
    result = convert_text(inp)
    status = "PASS" if result == expected else "FAIL"
    if status == "PASS":
        passed += 1
    print(f"[{status}] {desc}")
    if status == "FAIL":
        print(f"       Input:    {repr(inp)}")
        print(f"       Expected: {repr(expected)}")
        print(f"       Got:      {repr(result)}")

print(f"\n{passed}/{len(tests)} mapping tests passed.")

rt_passed = 0
for word in round_trips:
    result = convert_text(convert_text(word))
    status = "PASS" if result == word else "FAIL"
    if status == "PASS":
        rt_passed += 1
    print(f"[{status}] Round-trip: {repr(word)} → {repr(convert_text(word))} → {repr(result)}")

print(f"{rt_passed}/{len(round_trips)} round-trip tests passed.")
