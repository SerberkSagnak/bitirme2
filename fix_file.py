#!/usr/bin/env python3
"""
Script to fix the app_enhanced_v6.py file by removing only the problematic code block
"""

def fix_app_file():
    # Read the entire file
    with open('app_enhanced_v6.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # Find where the problematic section is and the next endpoint starts
    start_problem = None
    end_problem = None
    
    for i, line in enumerate(lines, 1):
        if "Problematic code block" in line:
            start_problem = i - 1  # Convert to 0-based index
            print(f"Found problem start at line {i}")
        elif line.strip().startswith('# === 🧠 NEW PURE DEEP LEARNING ENDPOINT ===') or line.strip().startswith('@app.get("/deep-learning-recommendations'):
            end_problem = i - 1  # Convert to 0-based index, don't include this line
            print(f"Found good code start at line {i}")
            break
    
    if start_problem is not None and end_problem is not None:
        print(f"Removing lines {start_problem + 1} to {end_problem}")
        
        # Create new content by removing problematic lines
        new_lines = (lines[:start_problem] + 
                    ["# Problematic code block was removed to fix syntax errors\n\n"] + 
                    lines[end_problem:])
        
        print(f"New total lines: {len(new_lines)}")
        
        # Write back to file
        with open('app_enhanced_v6.py', 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print("File fixed successfully!")
    else:
        print("Could not find problematic section boundaries")
        print(f"start_problem: {start_problem}, end_problem: {end_problem}")

if __name__ == "__main__":
    fix_app_file()
