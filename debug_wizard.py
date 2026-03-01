import random
import time
import sys

def print_slow(text, delay=0.05):
    """Prints text letter by letter for dramatic effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def fake_progress_bar():
    """Simulates a progress bar that lies about its progress."""
    print("\n[ Initializing Quantum Debugger v9000 ]")
    time.sleep(0.5)
    
    messages = [
        "Analyzing syntax...",
        "Consulting the internet...",
        "Checking if the moon is aligned...",
        "Petting the server cat...",
        "Blaming the intern...",
    ]

    for i in range(10):
        # Randomly pick a message
        msg = random.choice(messages)
        # Randomly pick a percentage that jumps around
        pct = random.randint(0, 100)
        
        # We use \r to overwrite the line
        print(f"\r[ {pct}% ] {msg}", end='', flush=True)
        time.sleep(0.4)
    
    print("\n\n") # Double newline to clear the progress line

def get_excuse():
    """Selects a random, nonsensical excuse."""
    excuses = [
        "The variable is having an identity crisis.",
        "There is a semicolon hiding in the basement.",
        "Your computer is tired of your code.",
        "The internet is currently buffering reality.",
        "You forgot to feed the electricity to the CPU.",
        "The indentation is shy and won't come out.",
        "A ghost is typing in the background.",
        "The bug is actually a feature we haven't monetized yet.",
        "It works on my machine... but my machine is a toaster.",
        "The code is working, but the universe is confused."
    ]
    return random.choice(excuses)

def get_solution():
    """Selects a random, unhelpful solution."""
    solutions = [
        "Solution: Reboot the universe.",
        "Solution: Type 'sudo' before every command. (Just kidding, don't do that.)",
        "Solution: Explain the problem to a rubber duck.",
        "Solution: Take a nap. The code will fix itself while you sleep.",
        "Solution: Delete the file and start over. (Wait, don't do that.)",
        "Solution: Stare at the screen until it apologizes."
    ]
    return random.choice(solutions)

def main():
    print_slow("\n========================================")
    print_slow("   THE DEBUGGING WIZARD   ")
    print_slow("========================================\n")
    
    print("Welcome, weary coder. I sense you have a problem.")
    print("Describe the issue (or just type 'panic'):")
    
    try:
        user_problem = input("\n> ")
    except KeyboardInterrupt:
        print("\n\nOh, you ran away. Typical.")
        return

    if user_problem.lower() == "panic":
        print_slow("Okay, okay! I'm helping! Don't panic!")
    
    fake_progress_bar()
    
    print_slow("Analysis Complete.")
    time.sleep(1)
    
    print("\n[ DIAGNOSIS ]")
    print(f"   {get_excuse()}")
    
    print("\n[ RECOMMENDED SOLUTION ]")
    print(f"   {get_solution()}")
    
    print("\n[ FINAL NOTE ]")
    print_slow("Remember: If you can't fix it, just blame the documentation.")
    print("\n========================================")
    
    # ASCII Cat to comfort you
    print("""
      |\      _,,,---,,_
      /,`.-'`'    -.  ;-;;,_
     |,4-  ) )-,_. ,\\ (  `'-'
    '---''(_/--'  `-\\_)
    (Don't worry, I'm not a real cat)
    """)

if __name__ == "__main__":
    main()
