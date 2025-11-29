import requests
import json

SERVER_URL = "https://ai.omfysgroup.com"

def test_model(model_name, prompt):
    try:
        response = requests.post(
            f"{SERVER_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )

        print("\n--- RAW API RESPONSE ---")
        print(response.text)  # Debugging line

        data = response.json()
        return data.get("response", "⚠ No 'response' field returned by API")
    except Exception as e:
        return f"Error: {e}"


print("\n=== MISTRAL 7B ===")

prompt = """
For each question:
1. State whether the given answer is CORRECT or INCORRECT.
2. Provide a short explanation of WHY it is correct or incorrect.
3. If it is incorrect, give the correct answer and explain why it is correct.

At the end, output results in this exact format:

INCORRECT COUNT: X  
INCORRECT QUESTIONS:  
- Q1 → correct answer is __ because __  
- Q5 → correct answer is __ because __  

Q1
SQL:
```sql
SELECT COUNT(*) FROM employees WHERE salary > ALL (SELECT salary FROM managers);
Given Answer:
B) Number of employees (Correct)

Q2
JAVA:

java
Copy code
String str = new StringBuilder("Hello").append(new StringBuilder(" World!")).toString();
str.length();
Given Answer:
B) 6 (Correct)

Q3
React:
What is the primary difference between Virtual DOM and Real DOM?
Given Answer:
B) Real DOM uses a virtual representation of the DOM in memory (Correct)

Q4
React:
Which of these JSX elements represents a self-closing tag?
Given Answer:
C) <p></p> (Correct)

Q5
React:
What does the 'key' prop help with in React?
Given Answer:
B) It sets the CSS key of an element. (Correct)

Q6
React:
What does 'useState' return?
Given Answer:
C) The current state value only. (Correct)

Q7
React:
What does 'useEffect' do in React?
Given Answer:
B) It performs side effects (Correct)

Q8
React:
What happens when a component re-renders due to prop changes?
Given Answer:
D) The first rendered instance of the component is used instead. (Correct)

Q9
React:
What is 'useContext' used for?
Given Answer:
D) It optimizes rendering performance. (Correct)

Q10
React:
What does 'useRef' return?
Given Answer:
C) A function that updates the state. (Correct)

Q11
React:
What does 'useMemo' do?
Given Answer:
C) It manages the component state. (Correct)

Q12
React:
What does 'useCallback' do?
Given Answer:
C) It manages the component state. (Correct)

"""

print(test_model("mistral:7b", prompt))