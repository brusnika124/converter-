def round_rect_points(x1, y1, x2, y2, radius):
    return [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]


def draw_round_rect(canvas, x1, y1, x2, y2, radius=12, **kwargs):
    return canvas.create_polygon(
        round_rect_points(x1, y1, x2, y2, radius),
        smooth=True,
        **kwargs,
    )
