# Flask app to greet users
from flask import Flask, request, render_template_string

app = Flask(__name__)


@app.route("/")
def home():
    return render_template_string(
        """
        <form method="post" action="/greet">
            <input type="text" name="name" placeholder="Enter your name">
            <input type="submit" value="Greet">
        </form>
    """
    )


@app.route("/greet", methods=["POST"])
def greet():
    name = request.form.get("name", "World")
    return render_template_string(f"Hello, {{{{ name }}}}!")


if __name__ == "__main__":
    app.run(debug=True)
