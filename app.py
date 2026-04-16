import gradio as gr

with gr.Blocks(title="Sentinel") as app:
    gr.Markdown("# Hello World!")

if __name__ == "__main__":
    app.launch()
