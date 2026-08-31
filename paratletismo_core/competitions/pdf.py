from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    PageBreak,
    Spacer,
    Table,
    TableStyle,
)


def _fmt_datetime(value):
    if not value:
        return ''
    return value.strftime('%d/%m/%Y %H:%M')


def _fmt_date(value):
    if not value:
        return ''
    return value.strftime('%d/%m/%Y')


def _fmt_time(value):
    if not value:
        return ''
    return value.strftime('%H:%M')


def _event_summary_lines(event):
    cats = list(event.categories.all()) if event.categories.exists() else ([event.category] if event.category else [])
    sexs = list(event.sexes.all()) if event.sexes.exists() else ([event.sex] if event.sex else [])
    fcs = list(event.functional_classifications.all()) if event.functional_classifications.exists() else ([event.functional_classification] if event.functional_classification else [])
    lines = [
        ('Disciplina', event.event_type.name if event.event_type else (event.discipline.name if event.discipline else '')),
        ('Sexo', ', '.join(s.name for s in sexs) or 'Libre'),
        ('Categoria', ', '.join(c.name for c in cats) or 'Libre'),
        ('Clasificacion', ', '.join(fc.code for fc in fcs) or 'Libre'),
    ]
    if event.scheduled_date:
        lines.append(('Fecha', _fmt_datetime(event.scheduled_date)))
    if event.scheduled_time:
        lines.append(('Hora', _fmt_time(event.scheduled_time)))
    if event.call_time:
        lines.append(('Camara de llamada', _fmt_time(event.call_time)))
    if event.venue_detail:
        lines.append(('Lugar', event.venue_detail))
    judges = list(event.judge_assignments.select_related('judge').all())
    if judges:
        head = [j for j in judges if j.is_head]
        rest = [j for j in judges if not j.is_head]
        names = []
        if head:
            names.append('Juez Principal: ' + head[0].judge.get_full_name())
        if rest:
            names.append('Jueces: ' + ', '.join(j.judge.get_full_name() for j in rest))
        lines.append(('Jueces', ' / '.join(names)))
    return lines


def _athlete_code(athlete):
    if athlete.functional_classification:
        return athlete.functional_classification.code
    if athlete.track_classification or athlete.field_classification:
        return (athlete.track_classification or athlete.field_classification).code
    return ''


def _event_header(title, event, athletes):
    tournament = event.tournament
    elements = []

    tstyle = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=16, alignment=TA_CENTER, spaceAfter=2)
    sstyle = ParagraphStyle('subtitle', fontName='Helvetica', fontSize=10, alignment=TA_CENTER)
    h1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=12, alignment=TA_LEFT, spaceBefore=8, spaceAfter=2)
    info_style = ParagraphStyle('info', fontName='Helvetica', fontSize=9)

    elements.append(Paragraph(title, tstyle))
    elements.append(Paragraph(tournament.name, sstyle))
    sede = ' - '.join(filter(None, [tournament.venue, tournament.city, tournament.province]))
    if sede:
        elements.append(Paragraph(sede, sstyle))
    dates = ' - '.join(filter(None, [_fmt_date(tournament.tournament_start), _fmt_date(tournament.tournament_end)]))
    if dates:
        elements.append(Paragraph(dates, sstyle))

    elements.append(Paragraph('Prueba: ' + event.name, h1))
    summary = _event_summary_lines(event)
    summary.append(('Inscriptos', str(len(athletes))))
    meta = Table(
        [[Paragraph('<b>%s</b>' % k, info_style), Paragraph(v, info_style)] for k, v in summary],
        colWidths=[42 * mm, 158 * mm],
    )
    meta.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta)
    elements.append(Spacer(1, 4 * mm))
    return elements


def _start_list_table(athletes, is_time_based, use_bibs=True):
    header = ['N°'] + (['Bib'] if use_bibs else []) + ['Atleta', 'Institucion']
    widths = [10 * mm] + ([12 * mm] if use_bibs else []) + [70 * mm, 55 * mm]
    if is_time_based:
        header += ['Carril', 'Clasif.', 'Tiempo', 'Tiempo Oficial', 'Lugar', 'Obs.']
        widths += [12 * mm, 16 * mm, 20 * mm, 24 * mm, 12 * mm, 20 * mm]
    else:
        header += ['Clasif.', '1', '2', '3', '4', '5', '6', 'Mejor', 'Lugar', 'Obs.']
        widths += [16 * mm, 12 * mm, 12 * mm, 12 * mm, 12 * mm, 12 * mm, 12 * mm, 14 * mm, 12 * mm, 20 * mm]

    ordered = sorted(athletes, key=lambda a: (a.lane if a.lane else 999, a.bib_number or 0))
    rows = [header]
    for i, a in enumerate(ordered, start=1):
        full_name = a.registration.athlete.user.get_full_name() or str(a.registration.athlete.user)
        row = [str(i)]
        if use_bibs:
            row.append(str(a.bib_number) if a.bib_number is not None else '')
        row += [
            full_name,
            a.registration.institution.name if a.registration.institution else '',
        ]
        code = _athlete_code(a.registration.athlete)
        if is_time_based:
            row += [str(a.lane) if a.lane is not None else '', code, '', '', '', '']
        else:
            row += [code, '', '', '', '', '', '', '', '', '']
        rows.append(row)

    body_style = ParagraphStyle('body', fontName='Helvetica', fontSize=9)
    body_data = [[Paragraph(str(c), body_style) for c in r] for r in rows]
    table = Table(body_data, colWidths=widths, repeatRows=1, rowHeights=[7 * mm] + [10 * mm] * (len(rows) - 1))
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.25, 0.25, 0.35)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return table


def _signatures(elements):
    elements.append(Spacer(1, 25 * mm))
    body_style = ParagraphStyle('body', fontName='Helvetica', fontSize=9)
    elements.append(Paragraph('Observaciones: ' + '_' * 120, body_style))
    elements.append(Spacer(1, 20 * mm))
    sig_row = Table([
        [Paragraph('<b>Firma Juez</b>', body_style), Paragraph('<b>Firma Camara de Llamada</b>', body_style), Paragraph('<b>Firma Foto Finish</b>', body_style)],
        ['', '', ''],
    ], colWidths=[83 * mm, 83 * mm, 84 * mm])
    sig_row.setStyle(TableStyle([
        ('LINEABOVE', (0, 1), (-1, 1), 0.6, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, 1), 15),
    ]))
    elements.append(sig_row)


def _render(elements):
    buf = BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='main')

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.drawString(doc.leftMargin, doc.bottomMargin - 8 * mm, 'Paratletismo - Documento oficial')
        canvas.drawRightString(doc.leftMargin + doc.width, doc.bottomMargin - 8 * mm, 'Pagina %d' % doc.page)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=on_page)])
    doc.build(elements)
    return buf.getvalue()


def _load_athletes(event):
    from paratletismo_core.competitions.models import AthleteEvent
    return list(
        AthleteEvent.objects.filter(tournament_event=event)
        .exclude(status='withdrawn')
        .select_related(
            'registration__athlete__user',
            'registration__athlete__functional_classification',
            'registration__athlete__track_classification',
            'registration__athlete__field_classification',
            'registration__institution',
        )
    )


def build_event_start_list_pdf(event):
    athletes = _load_athletes(event)
    if not athletes:
        return None
    is_time_based = bool(event.event_type and event.event_type.is_time_based)
    elements = _event_header('START LIST', event, athletes)
    elements.append(_start_list_table(athletes, is_time_based, event.tournament.use_bibs))
    _signatures(elements)
    return _render(elements)


def build_tournament_start_list_pdf(tournament):
    events = list(
        tournament.events
        .exclude(status='cancelled')
        .filter(is_final=True)
        .order_by('scheduled_date', 'name')
    )
    elements = []
    sections = 0
    for i, event in enumerate(events):
        athletes = _load_athletes(event)
        if not athletes:
            continue
        if sections > 0:
            elements.append(PageBreak())
        sections += 1
        is_time_based = bool(event.event_type and event.event_type.is_time_based)
        elements.extend(_event_header('START LIST', event, athletes))
        elements.append(_start_list_table(athletes, is_time_based, event.tournament.use_bibs))
    if sections == 0:
        return None
    return _render(elements)


def build_final_list_pdf(event):
    from paratletismo_core.competitions.models import FinalResult
    finals = list(
        FinalResult.objects.filter(tournament_event=event)
        .select_related('athlete__user', 'athlete__functional_classification', 'athlete__track_classification', 'athlete__field_classification', 'athlete__institution', 'verified_by')
        .order_by('rank')
    )
    if not finals:
        return None
    athletes = _load_athletes(event)
    elements = _event_header('RESULTADOS FINALES', event, athletes)

    from paratletismo_core.competitions.models import AthleteEvent
    bibs = {
        ae.registration.athlete_id: ae.bib_number
        for ae in AthleteEvent.objects.filter(tournament_event=event).select_related('registration')
        if ae.bib_number
    }

    header = (['Pos'] + (['Bib'] if event.tournament.use_bibs else []) + ['Atleta', 'Institucion', 'Clasif.', 'Marca', 'Puntos', 'Estado'])
    widths = ([10 * mm] + ([12 * mm] if event.tournament.use_bibs else []) + [60 * mm, 55 * mm, 18 * mm, 30 * mm, 16 * mm, 20 * mm])

    rows = [header]
    for fr in finals:
        estado = 'OK'
        if fr.is_dnf:
            estado = 'DNF'
        elif fr.is_dns:
            estado = 'DNS'
        elif fr.is_dq:
            estado = 'DQ'
        marca = fr.best_mark
        if fr.record_type:
            marca = (marca + '  (R)').strip()
        row = [str(fr.rank) if fr.rank is not None else '-']
        if event.tournament.use_bibs:
            row.append(str(bibs.get(fr.athlete_id, '')))
        row += [
            fr.athlete.user.get_full_name() or str(fr.athlete.user),
            fr.athlete.institution.name if fr.athlete.institution else '',
            _athlete_code(fr.athlete),
            marca,
            str(fr.points) if fr.points is not None else '',
            estado,
        ]
        rows.append(row)

    body_style = ParagraphStyle('body', fontName='Helvetica', fontSize=9)
    body_data = [[Paragraph(str(c), body_style) for c in r] for r in rows]
    table = Table(body_data, colWidths=widths, repeatRows=1, rowHeights=8 * mm)
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.25, 0.25, 0.35)),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(table)

    verified = sorted({fr.verified_by.get_full_name() for fr in finals if fr.verified_by})
    if verified:
        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph('Verificado por: ' + ', '.join(verified), body_style))

    elements.append(Spacer(1, 25 * mm))
    sig_style = ParagraphStyle('sig', fontName='Helvetica', fontSize=9, alignment=TA_CENTER)
    sig_row = Table([[Paragraph('<b>Firma</b>', sig_style)], ['']], colWidths=[100 * mm])
    sig_row.setStyle(TableStyle([
        ('LINEABOVE', (0, 1), (-1, 1), 0.6, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, 1), 15),
    ]))
    elements.append(sig_row)

    return _render(elements)
