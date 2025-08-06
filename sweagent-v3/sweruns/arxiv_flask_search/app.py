from flask import Flask, render_template, request
import arxiv

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    papers = []
    if request.method == "POST":
        keywords = request.form.get("keywords", "")

        # Create the arxiv search client
        search = arxiv.Search(
            query=keywords, max_results=10, sort_by=arxiv.SortCriterion.Relevance
        )

        # Process results
        for result in search.results():
            paper = {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "summary": result.summary,
                "entry_id": result.entry_id,
                "pdf_url": result.pdf_url,
            }
            papers.append(paper)

    return render_template("index.html", papers=papers)


if __name__ == "__main__":
    app.run(debug=True)
