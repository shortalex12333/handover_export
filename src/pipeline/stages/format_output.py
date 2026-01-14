"""
Stage 7: Format handovers into final report structure
"""
from typing import List, Dict
from datetime import datetime

from ..types import MergedHandover, FormattedReport, Priority


class FormatOutputStage:
    """
    Stage 7: Format handovers into final report structure

    n8n equivalent: "Final Formatter"
    """

    SECTION_ORDER = [
        'Electrical', 'Projects', 'Admin', 'Galley Laundry',
        'Risk', 'Fire Safety', 'Tenders', 'Logistics',
        'Deck', 'Financial', 'General Outstanding'
    ]

    def execute(self, handovers: List[MergedHandover]) -> FormattedReport:
        """Format handovers into structured report"""

        # Group by category
        sections: Dict[str, List[MergedHandover]] = {}
        for h in handovers:
            cat = h.category.value
            if cat not in sections:
                sections[cat] = []
            sections[cat].append(h)

        # Calculate statistics
        total_emails = sum(len(h.source_ids) for h in handovers)
        critical_count = sum(
            1 for h in handovers
            for a in h.actions if a.priority == Priority.CRITICAL
        )
        high_count = sum(
            1 for h in handovers
            for a in h.actions if a.priority == Priority.HIGH
        )

        meta = {
            'generatedAt': datetime.now().isoformat(),
            'totalSections': len(sections),
            'totalEmails': total_emails,
            'sectionsProcessed': len([s for s in sections.values() if s]),
            'criticalCount': critical_count,
            'highCount': high_count
        }

        # Generate HTML
        html = self._generate_html(sections, meta)

        return FormattedReport(
            meta=meta,
            sections=sections,
            html=html,
            generated_at=datetime.now()
        )

    def _generate_html(self, sections: Dict, meta: Dict) -> str:
        """Generate HTML report"""

        sections_html = ''
        for section_name in self.SECTION_ORDER:
            if section_name not in sections:
                continue

            handovers = sections[section_name]
            items_html = ''

            for h in handovers:
                actions_html = ''
                for a in h.actions:
                    priority_class = a.priority.value.lower()
                    sub_tasks = ''.join(f'<li>{st}</li>' for st in a.sub_tasks)
                    sub_tasks_html = f'<ul>{sub_tasks}</ul>' if sub_tasks else ''

                    actions_html += f'''
                        <div class="action-item">
                            <span class="priority {priority_class}">[{a.priority.value}]</span>
                            {a.task}
                            {sub_tasks_html}
                        </div>
                    '''

                sources_html = ''.join(
                    f'<a href="{s["link"]}" target="_blank">{s["shortId"]}</a> '
                    for s in h.source_ids
                )

                items_html += f'''
                    <div class="handover-item">
                        <h3>{h.subject}</h3>
                        <div class="summary">{h.summary}</div>
                        <div class="actions">{actions_html}</div>
                        <div class="sources">Source Emails: {sources_html}</div>
                    </div>
                '''

            sections_html += f'''
                <div class="section">
                    <div class="section-header">{section_name.upper()}</div>
                    {items_html}
                </div>
            '''

        return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Yacht Handover Report - {meta['generatedAt'][:10]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; }}
        h1 {{ text-align: center; color: #003366; }}
        .meta {{ text-align: center; margin-bottom: 30px; color: #666; }}
        .section {{ margin-bottom: 40px; border-top: 3px solid #003366; padding-top: 20px; }}
        .section-header {{ font-size: 16px; font-weight: bold; margin-bottom: 15px; }}
        .handover-item {{ margin-bottom: 25px; padding: 15px; border: 1px solid #ccc; border-radius: 6px; }}
        .handover-item h3 {{ margin-top: 0; color: #003366; }}
        .summary {{ font-style: italic; margin: 10px 0; }}
        .actions {{ margin: 15px 0; }}
        .action-item {{ margin: 8px 0; }}
        .priority {{ font-weight: bold; padding: 2px 6px; margin-right: 8px; }}
        .critical {{ color: #d32f2f; }}
        .high {{ color: #f57c00; }}
        .normal {{ color: #1976d2; }}
        .sources {{ font-size: 12px; color: #666; margin-top: 10px; }}
        .sources a {{ margin-right: 10px; }}
    </style>
</head>
<body>
    <h1>YACHT HANDOVER REPORT</h1>
    <div class="meta">
        Generated: {meta['generatedAt']}<br>
        Sections: {meta['totalSections']} | Emails Processed: {meta['totalEmails']}
    </div>
    {sections_html}
</body>
</html>
        '''
