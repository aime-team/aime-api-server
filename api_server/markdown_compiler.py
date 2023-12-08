import markdown
import os

class MarkDownCompiler():

	def compile(md_file, output_html_file, css_file=None):
		md = markdown.Markdown(extensions=['meta', 'attr_list', 'fenced_code', 'codehilite','nl2br', 'tables'])
		with open(md_file, "r") as file:
			markdown_text = file.read()

		html_body = md.convert(markdown_text)
		md_meta =  md.Meta
		default_title = os.path.basename(md_file)
		doc_title = md_meta.get('title', [default_title])[0]

		html_text = "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>%(title)s</title>" % { 'title' : doc_title }
		if css_file:
			html_text += "<link href=\"%(css_file)s\" type=\"text/css\" rel=\"stylesheet\" />" % { 'css_file' : css_file }
		html_text += "</head><body><div class=\"markdown-body\">"
		html_text += html_body
		html_text += "</div></body></html>"

		with open(output_html_file, "w") as file:
			file.write(html_text)
