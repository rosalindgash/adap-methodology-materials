import os
import json
import requests
import time
from datetime import datetime
from pathlib import Path

def main():
    # Your available models
    print("Available models on your system:")
    print("1. mistral:7b-instruct")
    print("2. gpt-oss:20b") 
    print("3. phi3:mini")
    
    choice = input("Choose model (1-3) or press Enter for mistral: ").strip()
    
    model_map = {
        "1": "mistral:7b-instruct",
        "2": "gpt-oss:20b", 
        "3": "phi3:mini",
        "": "mistral:7b-instruct"  # default
    }
    
    model = model_map.get(choice, "mistral:7b-instruct")
    
    print(f"Using model: {model}")
    
    # Test connection with correct model
    try:
        response = requests.post("http://localhost:11434/api/generate", 
            json={
                "model": model,
                "prompt": "Return JSON: {\"test\": \"success\"}",
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Connection successful!")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Simple document analysis
    input_folder = Path("unprocessed")
    output_folder = Path("processed")
    output_folder.mkdir(exist_ok=True)
    
    txt_files = list(input_folder.glob("*.txt"))
    print(f"Found {len(txt_files)} documents")
    
    for file_path in txt_files:
        print(f"Processing: {file_path.name}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        prompt = f"""Analyze this document about disabled scholars, researchers, or academics describing their adaptive practices. Return JSON with:

{{
  "author": "author name or unknown",
  "disabilities": ["conditions mentioned"],
  "constraint_motivations": [{{"quote": "why traditional academic pathways were inaccessible", "analysis": "brief note on structural barriers encountered"}}],
  "tool_adaptations": [{{"quote": "how they adapted digital tools for research/academic work", "analysis": "brief note on specific tool innovations"}}],
  "workflow_modifications": [{{"quote": "how they changed research or academic work patterns", "analysis": "brief note on temporal or procedural adaptations"}}],
  "success_redefinition": [{{"quote": "how they measure academic success differently", "analysis": "brief note on alternative metrics or pathways"}}],
  "institutional_gaps": [{{"quote": "what academic support or accommodations were missing", "analysis": "brief note on systemic failures"}}]
}}

IMPORTANT CODING GUIDELINES:
- constraint_motivations: Focus on WHY traditional PhD programs, research methods, or academic structures were inaccessible (energy limitations, health barriers, institutional gatekeeping, geographic constraints)
- tool_adaptations: Look for use of AI tools, automation, Python scripts, alternative software, free/open-source tools chosen because commercial options were inaccessible
- workflow_modifications: Identify changes to research timing (variable sessions, asynchronous work), methods (document analysis instead of fieldwork), or productivity patterns (energy-conscious design)
- success_redefinition: Note alternative pathways (PhD by Publication, independent scholarship), different productivity metrics, or valuing sustainability over speed
- institutional_gaps: Identify missing support (no research assistants, no library access, no accommodations, rigid requirements, lack of methodological flexibility)

Only include quotes that clearly demonstrate each category. If a category has no evidence, use an empty array [].

Document text:
{text}"""

        try:
            response = requests.post("http://localhost:11434/api/generate", 
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_text = result.get('response', '')
                
                # Try to extract JSON
                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                if start != -1 and end > start:
                    json_text = raw_text[start:end]
                    try:
                        analysis = json.loads(json_text)
                        analysis["processing_info"] = {
                            "model": model,
                            "processed_at": datetime.now().isoformat(),
                            "doc_id": file_path.stem
                        }
                    except:
                        analysis = {"error": "Could not parse JSON", "raw_response": raw_text[:500]}
                else:
                    analysis = {"error": "No JSON found", "raw_response": raw_text[:500]}
            else:
                analysis = {"error": f"API error {response.status_code}"}
                
        except Exception as e:
            analysis = {"error": str(e)}
        
        # Save result
        output_file = output_folder / f"{file_path.stem}_coded.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved: {output_file}")

if __name__ == "__main__":
    main()
