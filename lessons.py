LESSONS = [
    {
        "id": 1,
        "title": "Variables and Data Types",
        "explanation": """\
Python has four basic data types:
  int    – whole numbers:       42, -5, 0
  float  – decimal numbers:     3.14, -0.5
  str    – text:                "hello", 'world'
  bool   – logical values:      True, False

Variables need no type declaration:
  age   = 25          # int
  name  = "Alice"     # str
  pi    = 3.14        # float
  admin = True        # bool

Check types with type():  type(age) → <class 'int'>
Format output with f-strings:  f"Hello, {name}!" """,
        "example": """\
# Assigning variables
age     = 25
name    = "Alice"
height  = 1.75
student = True

# Checking types
print(type(age))     # <class 'int'>
print(type(name))    # <class 'str'>

# f-string formatting
print(f"Name: {name}, Age: {age}")
print(f"Height: {height}m, Student: {student}")""",
        "exercise": """\
Create a person's profile using four variables:
  - name        (string  – any name)
  - age         (int     – any age)
  - height      (float   – in metres, e.g. 1.75)
  - is_employed (bool    – True or False)

Then print them in exactly this format (values will differ):
  "Name: Alice, Age: 30, Height: 1.75m, Employed: True"

Requirements:
  1. Use exactly those four variable names
  2. Use a single f-string for the print""",
        "hints": [
            "f-string syntax: f\"Name: {name}\"",
            "Boolean literals are capitalised: True / False",
        ],
    },
    {
        "id": 2,
        "title": "Strings and String Methods",
        "explanation": """\
Strings are sequences of characters. Handy methods:
  .upper() / .lower()   – change case
  .strip()              – remove surrounding whitespace
  .split(sep)           – split into a list
  .join(list)           – join list items into a string
  .replace(old, new)    – substitute text
  len(s)                – number of characters

Slicing:  s[start:end:step]
  text = "Python"
  text[0:3]   →  "Pyt"
  text[::-1]  →  "nohtyP"   (reversed)""",
        "example": """\
sentence = "  Hello, World!  "

clean = sentence.strip()
print(clean)              # Hello, World!
print(clean.upper())      # HELLO, WORLD!
print(clean.lower())      # hello, world!

words = clean.split(", ")
print(words)              # ['Hello', 'World!']
print(" – ".join(words))  # Hello – World!

text = "Python"
print(text[0:3])   # Pyt
print(text[::-1])  # nohtyP""",
        "exercise": """\
Write a function called process_text(text) that:
  1. Removes leading and trailing whitespace
  2. Converts to uppercase
  3. Replaces every space with an underscore
  4. Returns the result

Example:
  process_text("  hello world  ") → "HELLO_WORLD"

Then call it and print the result:
  print(process_text("  hello world  "))""",
        "hints": [
            "Chain methods: text.strip().upper().replace(' ', '_')",
            "Or apply each step separately with intermediate variables",
        ],
    },
    {
        "id": 3,
        "title": "Lists",
        "explanation": """\
Lists are ordered, mutable sequences:
  fruits = ["apple", "banana", "cherry"]

Common operations:
  fruits[0]            → "apple"           (index from start)
  fruits[-1]           → "cherry"          (index from end)
  fruits[1:3]          → ["banana","cherry"] (slice)
  fruits.append(x)     → add to the end
  fruits.insert(i, x)  → insert at position i
  fruits.remove(x)     → remove first occurrence of x
  fruits.pop(i)        → remove and return element at i
  fruits.sort()        → sort in-place
  sorted(fruits)       → return a sorted copy
  len(fruits)          → number of elements
  x in fruits          → membership test""",
        "example": """\
numbers = [3, 1, 4, 1, 5, 9, 2, 6]

print(numbers[0])    # 3
print(numbers[-1])   # 6

numbers.append(5)
numbers.insert(0, 0)
numbers.sort()
print(numbers)

print(len(numbers))
print(sum(numbers))
print(max(numbers), min(numbers))""",
        "exercise": """\
Create a list called 'scores' with these values:
  [85, 92, 78, 95, 88, 72, 90]

Write code that:
  1. Prints the highest score
  2. Prints the lowest score
  3. Prints the average (rounded to 2 decimal places)
  4. Appends the score 88
  5. Sorts the list ascending
  6. Prints the final sorted list

Expected output format:
  High: 95
  Low: 72
  Average: 85.71
  Sorted: [72, 78, 85, 88, 88, 90, 92, 95]""",
        "hints": [
            "average = sum(scores) / len(scores)",
            "Use f\"{avg:.2f}\" for two decimal places",
        ],
    },
    {
        "id": 4,
        "title": "Dictionaries",
        "explanation": """\
Dictionaries store key–value pairs:
  person = {"name": "Alice", "age": 30}

Common operations:
  d["key"]          → get value (KeyError if missing)
  d.get("key")      → get value (None if missing)
  d.get("key", 0)   → get value with a default
  d["key"] = val    → add or update
  del d["key"]      → delete a key
  "key" in d        → check existence
  d.keys()          → view of all keys
  d.values()        → view of all values
  d.items()         → view of (key, value) pairs
  d.update(other)   → merge another dict in""",
        "example": """\
student = {
    "name": "Alice",
    "grade": "A",
    "scores": [95, 87, 92],
}

print(student["name"])           # Alice
print(student.get("age", 0))    # 0  (default)

student["age"] = 20
student["scores"].append(88)

for key, value in student.items():
    print(f"{key}: {value}")""",
        "exercise": """\
Create a dictionary called 'inventory' with:
  "apples": 50,  "bananas": 30,  "oranges": 45,  "grapes": 0

Write code that:
  1. Prints all items that are in stock (quantity > 0)
     Format: "In stock: apples (50), bananas (30), oranges (45)"
  2. Adds "mangoes": 25
  3. Updates "bananas" to 35
  4. Prints the total quantity of all items
     Format: "Total items: 155" """,
        "hints": [
            "Iterate with: for name, qty in inventory.items():",
            "Build the in-stock string by filtering items where qty > 0",
        ],
    },
    {
        "id": 5,
        "title": "Conditionals (if / elif / else)",
        "explanation": """\
Conditionals branch execution based on truth values:

  if condition:
      ...
  elif other_condition:
      ...
  else:
      ...

Comparison:  ==  !=  <  >  <=  >=
Logical:     and   or   not
Membership:  in   not in

One-liner (ternary):
  label = "Pass" if score >= 60 else "Fail" """,
        "example": """\
score = 75

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
elif score >= 60:
    grade = "D"
else:
    grade = "F"

print(f"Score {score}: Grade {grade}")

status = "Pass" if score >= 60 else "Fail"
print(status)""",
        "exercise": """\
Write a function called classify_bmi(weight_kg, height_m) that:
  - Calculates BMI = weight / height²
  - Returns a category string:
      BMI < 18.5          → "Underweight"
      18.5 <= BMI < 25    → "Normal"
      25   <= BMI < 30    → "Overweight"
      BMI >= 30           → "Obese"

Test with:
  print(classify_bmi(50, 1.70))    # Underweight
  print(classify_bmi(70, 1.75))    # Normal
  print(classify_bmi(85, 1.70))    # Overweight
  print(classify_bmi(100, 1.70))   # Obese""",
        "hints": [
            "BMI formula: bmi = weight_kg / (height_m ** 2)",
            "Check ranges in order from lowest to highest",
        ],
    },
    {
        "id": 6,
        "title": "For Loops",
        "explanation": """\
For loops iterate over any sequence:

  for item in sequence:
      # use item

range() generates numbers:
  range(5)         → 0 1 2 3 4
  range(1, 6)      → 1 2 3 4 5
  range(0, 10, 2)  → 0 2 4 6 8

enumerate() adds an index:
  for i, val in enumerate(items, start=1):

zip() pairs two sequences:
  for a, b in zip(list1, list2):

break   – exit the loop early
continue – skip the rest of this iteration""",
        "example": """\
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit.upper())

for i in range(1, 6):
    print(f"{i}² = {i**2}")

for i, fruit in enumerate(fruits, 1):
    print(f"{i}. {fruit}")

numbers = [4, 7, 2, 9, 1]
for n in numbers:
    if n > 5:
        print(f"First > 5: {n}")
        break""",
        "exercise": """\
Write a function called fizzbuzz(n) that prints numbers from 1 to n:
  - Print "FizzBuzz" for multiples of both 3 and 5
  - Print "Fizz"     for multiples of 3 only
  - Print "Buzz"     for multiples of 5 only
  - Print the number itself otherwise

Call fizzbuzz(20) to test it.

Expected start of output:
  1
  2
  Fizz
  4
  Buzz
  Fizz
  7
  8
  Fizz
  Buzz
  11
  Fizz
  13
  14
  FizzBuzz  ...""",
        "hints": [
            "Check the FizzBuzz condition FIRST (divisible by both 3 and 5)",
            "Use modulo: n % 3 == 0 tests divisibility by 3",
        ],
    },
    {
        "id": 7,
        "title": "Functions",
        "explanation": """\
Functions package reusable logic:

  def function_name(param, optional="default"):
      \"\"\"Docstring: what this function does.\"\"\"
      # body
      return result

Key ideas:
  - Parameters are inputs; return sends a value back
  - Default values make arguments optional
  - *args accepts any number of positional arguments
  - **kwargs accepts any number of keyword arguments
  - Keep each function focused on one task""",
        "example": """\
def greet(name, greeting="Hello"):
    \"\"\"Return a personalised greeting.\"\"\"
    return f"{greeting}, {name}!"

print(greet("Alice"))          # Hello, Alice!
print(greet("Bob", "Hi"))      # Hi, Bob!


def stats(numbers):
    \"\"\"Return min, max, and average of a list.\"\"\"
    return min(numbers), max(numbers), sum(numbers) / len(numbers)

lo, hi, avg = stats([3, 1, 4, 1, 5, 9])
print(f"Min: {lo}, Max: {hi}, Avg: {avg:.2f}")""",
        "exercise": """\
Write a function called calculate_discount(price, discount_percent):
  - Validates inputs:
      price must be > 0  (raise ValueError("Price must be positive"))
      discount must be 0–100  (raise ValueError("Discount must be 0-100"))
  - Returns the discounted price as a float

Write a function called apply_bulk_discount(prices, discount):
  - Accepts a list of prices and a discount percentage
  - Returns a new list of discounted prices

Test with:
  print(calculate_discount(100, 20))        # 80.0
  print(calculate_discount(50, 10))         # 45.0
  print(apply_bulk_discount([100, 200, 300], 15))  # [85.0, 170.0, 255.0]""",
        "hints": [
            "Discounted price = price * (1 - discount / 100)",
            "Use a list comprehension in apply_bulk_discount",
        ],
    },
    {
        "id": 8,
        "title": "List Comprehensions",
        "explanation": """\
List comprehensions build lists in one readable line:

  [expression  for item in iterable  if condition]

Equivalent long-form:
  result = []
  for item in iterable:
      if condition:
          result.append(expression)

Dict comprehension:   {k: v for k, v in pairs}
Set comprehension:    {x for x in items}

Use them when the logic is simple; prefer a normal
loop for complex multi-step transformations.""",
        "example": """\
squares = [x**2 for x in range(1, 6)]
print(squares)   # [1, 4, 9, 16, 25]

evens = [x for x in range(20) if x % 2 == 0]
print(evens)     # [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

words = ["hello", "world", "python"]
upper = [w.upper() for w in words]
print(upper)     # ['HELLO', 'WORLD', 'PYTHON']

lengths = {w: len(w) for w in words}
print(lengths)   # {'hello': 5, 'world': 5, 'python': 6}""",
        "exercise": """\
Using list/dict comprehensions, create and print:

  1. 'squares'   – squares of 1 through 10
  2. 'evens'     – even numbers from 1 to 50
  3. 'long_words' – words longer than 4 chars from:
       words = ["cat", "python", "dog", "programming", "art", "code"]
  4. 'word_info' – dict mapping each word to its length

Expected output:
  [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
  [2, 4, 6, 8, ..., 50]
  ['python', 'programming']
  {'cat': 3, 'python': 6, 'dog': 3, 'programming': 11, 'art': 3, 'code': 4}""",
        "hints": [
            "[x**2 for x in range(1, 11)]  – note range goes to 11",
            "Filter with:  if len(w) > 4",
        ],
    },
    {
        "id": 9,
        "title": "Error Handling",
        "explanation": """\
Handle exceptions so your program doesn't crash:

  try:
      risky_code()
  except SpecificError as e:
      handle_it(e)
  except (Error1, Error2):
      handle_either()
  else:
      runs_only_if_no_exception()
  finally:
      always_runs()

Common built-in exceptions:
  ValueError         – wrong value for this type
  TypeError          – wrong type entirely
  KeyError           – dict key not found
  IndexError         – list index out of range
  ZeroDivisionError  – dividing by zero
  FileNotFoundError  – file doesn't exist

Raise your own:  raise ValueError("message")""",
        "example": """\
def safe_divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        return "Error: cannot divide by zero"
    except TypeError:
        return "Error: both arguments must be numbers"
    else:
        return result
    finally:
        print("Division attempted")

print(safe_divide(10, 2))    # 5.0
print(safe_divide(10, 0))    # Error: cannot divide by zero
print(safe_divide(10, "x"))  # Error: both arguments must be numbers""",
        "exercise": """\
Write a function called safe_parse_int(value):
  - Tries to convert value to int
  - Returns the int if successful
  - On failure prints: "Cannot convert '{value}' to int"
    and returns None

Write a function called process_data(data_list):
  - Applies safe_parse_int to every item
  - Returns a list containing only the successful conversions

Test with:
  print(safe_parse_int("42"))    # 42
  print(safe_parse_int("abc"))   # None  (+ prints warning)
  data = ["1", "two", "3", "four", "5"]
  print(process_data(data))      # [1, 3, 5]""",
        "hints": [
            "Catch ValueError when int() is given a non-numeric string",
            "In process_data, build the list by filtering out None results",
        ],
    },
    {
        "id": 10,
        "title": "Classes and OOP Basics",
        "explanation": """\
A class is a blueprint for creating objects:

  class MyClass:
      def __init__(self, x, y):   # constructor
          self.x = x              # instance attribute
          self.y = y

      def method(self):           # instance method
          return self.x + self.y

      def __str__(self):          # called by print()
          return f"MyClass({self.x}, {self.y})"

Creating and using an object:
  obj = MyClass(3, 4)
  print(obj)          # MyClass(3, 4)
  print(obj.method()) # 7""",
        "example": """\
class Rectangle:
    def __init__(self, width, height):
        self.width  = width
        self.height = height

    def area(self):
        return self.width * self.height

    def perimeter(self):
        return 2 * (self.width + self.height)

    def __str__(self):
        return f"Rectangle({self.width}x{self.height})"


r = Rectangle(5, 3)
print(r)              # Rectangle(5x3)
print(r.area())       # 15
print(r.perimeter())  # 16""",
        "exercise": """\
Create a class called BankAccount:

  __init__(self, owner, balance=0)
    – stores owner name and starting balance

  deposit(self, amount)
    – adds amount to balance
    – raise ValueError("Amount must be positive") if amount <= 0

  withdraw(self, amount)
    – subtracts amount from balance
    – raise ValueError("Amount must be positive") if amount <= 0
    – raise ValueError("Insufficient funds") if amount > balance

  get_balance(self)
    – returns current balance

  __str__(self)
    – returns "BankAccount(Alice, balance: $100.00)"

Test with:
  acc = BankAccount("Alice", 100)
  print(acc)                # BankAccount(Alice, balance: $100.00)
  acc.deposit(50)
  acc.withdraw(30)
  print(acc.get_balance())  # 120.0
  acc.withdraw(200)         # should raise ValueError""",
        "hints": [
            "Use f\"{self.balance:.2f}\" to format money with 2 decimal places",
            "Test the error case inside a try/except block",
        ],
    },
]
