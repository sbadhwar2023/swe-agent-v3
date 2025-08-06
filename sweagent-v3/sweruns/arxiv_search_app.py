from flask import Flask, request, jsonify, render_template
import arxiv

app = Flask(__name__)


@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Arxiv Paper Search</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .search-container { margin-bottom: 20px; }
            .paper { margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; }
            input[type="text"] { width: 300px; padding: 5px; }
            button { padding: 5px 10px; }
        </style>
    </head>
    <body>
        <h1>Arxiv Paper Search</h1>
        <div class="search-container">
            <form action="/search" method="get">
                <input type="text" name="query" placeholder="Enter keywords...">
                <button type="submit">Search</button>
            </form>
        </div>
        <div id="results"></div>
    </body>
    </html>
    """


@app.route("/search")
def search():
    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "No query provided"})

    try:
        # Create a client with appropriate parameters
        client = arxiv.Client()

        # Create a search query
        search = arxiv.Search(
            query=query, max_results=10, sort_by=arxiv.SortCriterion.Relevance
        )

        # Execute the search
        results = []
        for paper in client.results(search):
            results.append(
                {
                    "title": paper.title,
                    "authors": [author.name for author in paper.authors],
                    "summary": paper.summary,
                    "pdf_url": paper.pdf_url,
                    "published": paper.published.strftime("%Y-%m-%d"),
                    "arxiv_url": paper.entry_id,
                }
            )

        # Create HTML response
        html_response = "<h2>Search Results:</h2>"
        for paper in results:
            html_response += f"""
            <div class="paper">
                <h3><a href="{paper['arxiv_url']}" target="_blank">{paper['title']}</a></h3>
                <p><strong>Authors:</strong> {', '.join(paper['authors'])}</p>
                <p><strong>Published:</strong> {paper['published']}</p>
                <p><strong>Summary:</strong> {paper['summary'][:300]}...</p>
                <p><a href="{paper['pdf_url']}" target="_blank">Download PDF</a></p>
            </div>
            """

        return html_response

    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)
