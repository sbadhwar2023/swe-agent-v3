#!/usr/bin/env python3

import arxiv
import argparse
from typing import List, Dict
import textwrap


def search_arxiv(keywords: str, max_results: int = 10) -> List[Dict]:
    """
    Search arXiv for papers matching the given keywords

    Args:
        keywords: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of papers with their details
    """
    search = arxiv.Search(
        query=keywords, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
    )

    papers = []
    for result in search.results():
        paper = {
            "title": result.title,
            "authors": ", ".join(author.name for author in result.authors),
            "summary": result.summary,
            "published": result.published.strftime("%Y-%m-%d"),
            "pdf_url": result.pdf_url,
            "entry_id": result.entry_id,
        }
        papers.append(paper)

    return papers


def display_papers(papers: List[Dict]):
    """Display papers in a formatted way"""
    for i, paper in enumerate(papers, 1):
        print(f"\n{'-'*80}")
        print(f"{i}. {paper['title']}")
        print(f"Authors: {paper['authors']}")
        print(f"Published: {paper['published']}")
        print("\nSummary:")
        # Wrap summary text for better readability
        wrapped_summary = textwrap.wrap(paper["summary"], width=75)
        print("\n".join(wrapped_summary))
        print(f"\nPDF: {paper['pdf_url']}")
        print(f"arXiv ID: {paper['entry_id']}")


def main():
    parser = argparse.ArgumentParser(description="Search arXiv for research papers")
    parser.add_argument("keywords", type=str, help="Keywords to search for")
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )

    args = parser.parse_args()

    print(f"\nSearching arXiv for: {args.keywords}")
    print("Please wait...\n")

    try:
        papers = search_arxiv(args.keywords, args.max_results)
        if papers:
            display_papers(papers)
        else:
            print("No papers found matching your search criteria.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
