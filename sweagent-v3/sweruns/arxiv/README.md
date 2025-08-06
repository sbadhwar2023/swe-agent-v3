# arXiv Paper Search

A simple command-line tool to search for relevant papers on arXiv based on keywords.

## Installation

1. Make sure you have Python 3.6+ installed
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script with your search keywords:

```bash
python arxiv_search.py "quantum computing"
```

Optional arguments:
- `--max-results N`: Specify maximum number of results (default: 10)

Example with maximum results:
```bash
python arxiv_search.py "machine learning" --max-results 5
```

## Features

- Searches arXiv for papers matching your keywords
- Displays:
  - Paper title
  - Authors
  - Publication date
  - Abstract summary
  - PDF download link
  - arXiv ID
- Results are sorted by relevance
- Text wrapping for better readability

## Output Format

For each paper, the tool displays:
- Title
- Author list
- Publication date
- Summary/Abstract
- Direct link to PDF
- arXiv ID

## Error Handling

The script includes basic error handling for:
- Network issues
- Invalid search queries
- No results found