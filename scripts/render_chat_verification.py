"""Read UTF-8 browser evidence explicitly, including on legacy Windows locales."""
import json
from pathlib import Path

def render_report(source=Path('runtime/expanded-browser-results.json'),destination=Path('runtime/answer-presentation-results.md')):
    report=json.loads(source.read_text(encoding='utf-8'))
    wanted={'Can cetirizine make me feel sleepy?','Do antibiotics treat colds?','What are the symptoms of dehydration?'}
    parts=['# Actual browser chatbot answers','Captured through the real chat composer. Source quotations and links below are the unmodified API response.']
    for row in report['results']:
        if row['question'] not in wanted:continue
        parts.extend(['## '+row['question'],row['answer'],'### Citation links'])
        parts.extend(f"[{i}] [{citation['title']}]({citation['url']}) — {citation['section']}" for i,citation in enumerate(row['citations'],1))
    destination.write_text('\n\n'.join(parts)+'\n',encoding='utf-8')
    print(f'Wrote UTF-8 answer report: {destination}')

if __name__=='__main__':render_report()
