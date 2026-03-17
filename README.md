
# Reproducibility Materials

This repository contains scripts and data from:

**Gash, R. (forthcoming). Implementing Energy-Conscious Automation: A Reproducible Workflow.**

## Overview

These materials support reproducible research using AI-assisted document analysis designed for energy-conscious qualitative research. The methodology reduces procedural cognitive load by approximately 85% compared to traditional qualitative methods, enabling disabled researchers' participation in knowledge production.

## Repository Contents

- **`batch_analyzer.py`** - Python script for AI-assisted qualitative coding using Ollama
- **`fetch_personal_narratives.py`** - Python script for retrieving web-based documents
- **`corpus_metadata.csv`** - Metadata for 31 unique publicly accessible narratives analyzed in the study
- **`README.md`** - This file

## System Requirements

### Software
- **Python**: 3.10 or higher
- **Ollama**: Latest version ([Download here](https://ollama.ai/))
- **Operating System**: Windows, macOS, or Linux

### Python Packages
```bash
pip install requests
```

### AI Model
Download Mistral 7B-Instruct (used in the original study):
```bash
ollama pull mistral:7b-instruct
```

**Alternative models** (if Mistral doesn't work on your system):
```bash
ollama pull phi3:mini        # Faster, less memory
ollama pull gpt-oss:20b      # Higher quality, more memory
```

## Installation

1. **Install Ollama** from https://ollama.ai/
2. **Download a model**:
```bash
   ollama pull mistral:7b-instruct
```
3. **Clone this repository**:
```bash
   git clone https://github.com/rosalindgash/adap-methodology-materials.git
   cd [repo-name]
```
4. **Install Python dependencies**:
```bash
   pip install requests
```

## Usage

### Step 1: Start Ollama

Open a terminal and run:
```bash
ollama serve
```

Leave this terminal window open while using the scripts.

### Step 2: Prepare Your Documents

Create a folder called `unprocessed/` and place your `.txt` files there:
```
your-project/
├── unprocessed/
│   ├── document001.txt
│   ├── document002.txt
│   └── document003.txt
├── batch_analyzer.py
└── fetch_personal_narratives.py
```

### Step 3: Run the Batch Analyzer
```bash
python3 batch_analyzer.py
```

When prompted, choose your model:
- Press **Enter** for default (Mistral 7B-Instruct)
- Or type **1**, **2**, or **3** for specific models

### Step 4: Review Results

Coded documents appear in the `processed/` folder as JSON files:
```
processed/
├── document001_coded.json
├── document002_coded.json
└── document003_coded.json
```

## Understanding the Output

Each JSON file contains:
- **author**: Document author or "unknown"
- **disabilities**: Conditions mentioned
- **constraint_motivations**: Why traditional paths were inaccessible
- **tool_adaptations**: Digital tool innovations
- **workflow_modifications**: Research process changes
- **success_redefinition**: Alternative success metrics
- **institutional_gaps**: Missing support/accommodations
- **processing_info**: Metadata about the analysis

## Coding Framework

The script applies the **Adaptive Digital Academic Practice (ADAP)** framework, coding for:

1. **Constraint Motivations** - Structural barriers in traditional academic pathways
2. **Tool Adaptations** - Strategic use of digital technologies
3. **Workflow Modifications** - Changes to research timing/methods
4. **Success Redefinition** - Alternative pathways (PhD by Publication, independent scholarship)
5. **Institutional Gaps** - Missing accommodations or support

## Validation

The original study achieved **84% inter-rater agreement** between AI-assisted and manual coding across a 16% random sample (5 of 31 documents).

For validation in your own research:
1. Manually code 10-15% of documents
2. Compare with AI output
3. Calculate agreement rate
4. Refine prompts if agreement < 80%

## Energy-Conscious Design Principles

This workflow embodies:
- **Automate procedural, not interpretive labor** - AI handles quote extraction; humans interpret meaning
- **Preserve researcher authority** - All analytical decisions remain human-controlled
- **Enable variable engagement** - Work in small batches matching daily energy availability
- **Maintain transparency** - All AI outputs are reviewable and auditable

## Troubleshooting

**"Connection failed" error:**
- Ensure Ollama is running: `ollama serve`
- Check port 11434 is not blocked by firewall

**"Model not found" error:**
- Download the model: `ollama pull mistral:7b-instruct`
- Verify installation: `ollama list`

**"Could not parse JSON" in output:**
- AI response was malformed
- Check `raw_response` field in JSON file
- Consider refining prompt or trying different model

**Slow processing:**
- Mistral typically takes 30-60 seconds per document
- Phi3:mini is faster but less accurate
- Ensure no other heavy applications are running

## Citation

If you use these materials, please cite:
```
Gash, R. (forthcoming). Energy-Conscious Qualitative Analysis: Automation 
as Accessibility in Adaptive Digital Academic Practice for Disabled Researchers. 
[Journal details pending publication]
```

## License

MIT License

Copyright (c) 2025 Rosalind Gash

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contact

Rosalind Gash  
Email: rrgash@protonmail.com  
ORCID: https://orcid.org/0009-0005-9931-0766

## Acknowledgments

This research demonstrates that automation functions as accessibility intervention enabling disabled researchers' full participation in knowledge production, not merely as efficiency enhancement for able-bodied scholars.

---


**Note:** The document corpus analyzed in the original study consists of publicly accessible narratives by disabled scholars. The `corpus_metadata.csv` file contains URLs and publication dates for the 31 unique narratives, enabling replication of the analysis or extension to new corpora.
