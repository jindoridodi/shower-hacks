"""Conservative Markdown cleanup; no inferred site-specific boilerplate rules."""
import re


def clean_markdown(markdown: str, *, confirmed_boilerplate: tuple[str, ...] = ()) -> str:
    """Remove only caller-confirmed exact blocks, outside fenced code.

    Supply boilerplate from inspected site samples, never from keyword matches.
    Preserve indentation, Markdown hard breaks, tables, links and code whitespace.
    """
    text = markdown.replace('\r\n', '\n').replace('\r', '\n')
    output: list[str] = []
    fence = None
    for line in text.split('\n'):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if fence:
            output.append(line)
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*', line):
                fence = None
            continue
        if marker:
            fence = marker[1]
            output.append(line)
            continue
        if line.startswith(('    ', '\t')):
            output.append(line)
            continue
        line = line.rstrip() + ('  ' if line.strip() and line.endswith('  ') else '')
        if line in confirmed_boilerplate:
            continue
        if not line and (not output or output[-1] == ''):
            continue
        output.append(line)
    while output and output[-1] == '':
        output.pop()
    return '\n'.join(output)
