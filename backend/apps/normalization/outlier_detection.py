import statistics
from .models import NormalizedActivity
from .flags import FLAG_MESSAGES


def run_outlier_detection(batch):
    rows = NormalizedActivity.objects.filter(
        batch=batch,
        co2e_kg__isnull=False
    ).exclude(status='REJECTED')

    by_subtype = {}
    for row in rows:
        key = row.activity_subtype
        by_subtype.setdefault(key, []).append(row)

    for subtype, group in by_subtype.items():
        if len(group) < 3:
            continue
        values = [float(r.co2e_kg) for r in group]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        for row in group:
            val = float(row.co2e_kg)
            changed = False
            if val > mean + 3 * stdev:
                if 'OUTLIER_HIGH' not in row.flags:
                    row.flags = row.flags + ['OUTLIER_HIGH']
                    changed = True
            elif val < mean - 3 * stdev and val > 0:
                if 'OUTLIER_LOW' not in row.flags:
                    row.flags = row.flags + ['OUTLIER_LOW']
                    changed = True
            if changed:
                row.flag_summary = ' | '.join(FLAG_MESSAGES.get(f, f) for f in row.flags)
                row.status = 'FLAGGED'
                row.save(update_fields=['flags', 'flag_summary', 'status'])
