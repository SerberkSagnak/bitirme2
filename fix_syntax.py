"""
Ana dosyadaki syntax hatalarını düzelt
"""

def fix_app_enhanced_v6():
    print("=== SYNTAX REPAIR ===")
    
    # Read file
    with open('app_enhanced_v6.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Total lines: {len(lines)}")
    
    # Find problematic section
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if "OLD ENDPOINT COMPLETELY REMOVED" in line:
            start_line = i
            print(f"Problematic section starts at line: {i+1}")
        
        if "NEW PURE DEEP LEARNING ENDPOINT" in line:
            end_line = i
            print(f"Clean section starts at line: {i+1}")
            break
    
    if start_line is not None and end_line is not None:
        print(f"Removing problematic lines {start_line+1} to {end_line}")
        
        # Keep everything before problematic section and after clean section
        clean_lines = lines[:start_line+1] + lines[end_line:]
        
        # Write clean version
        with open('app_enhanced_v6_clean.py', 'w', encoding='utf-8') as f:
            f.writelines(clean_lines)
        
        print("✅ Clean version created: app_enhanced_v6_clean.py")
        return True
    else:
        print("❌ Could not find problematic section")
        return False

if __name__ == "__main__":
    fix_app_enhanced_v6()
