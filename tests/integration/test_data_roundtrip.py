"""Exercise the public importer with small, synthetic cycler exports."""
import csv
from io import StringIO

import openpyxl
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from pbdp import Parser


@pytest.mark.parametrize('extension', ['.csv', '.txt', '.mpt', '.DTA', '.xlsx'])
def test_import_and_parquet_roundtrip(tmp_path, extension):
    source = tmp_path / ('synthetic' + extension)
    rows = [
        ['Technique started on : 21/10/2026 09:00:00'],
        ['time/s', '<I>/mA', 'Ecell/V', '(Q-Qo)/mA.h'],
        [0, 1000, 3.7, 0],
        [10, -500, 3.6, 500],
        [20, 0, 3.6, 500],
    ]
    if extension == '.xlsx':
        book = openpyxl.Workbook()
        for row in rows:
            book.active.append(row)
        book.save(source)
        book.close()
    else:
        stream = StringIO(newline='')
        delimiter = ',' if extension == '.csv' else '\t'
        csv.writer(stream, delimiter=delimiter).writerows(rows)
        source.write_text(stream.getvalue(), encoding='utf-8')
    original = source.read_bytes()
    result = Parser().data_importer(
        source, save_option='save all', state_option='yes', file_type='parquet'
    )
    assert result['Time [s]'].tolist() == [0, 10, 20]
    assert result['Current [A]'].tolist() == pytest.approx([1, -0.5, 0])
    assert result['Voltage [V]'].tolist() == pytest.approx([3.7, 3.6, 3.6])
    assert result['AmpHrs [Ah]'].tolist() == pytest.approx([0, 0.5, 0.5])
    assert result['Battery State'].tolist() == ['charging', 'discharging', 'rest']
    start = pd.Timestamp('2026-10-21 09:00:00')
    assert result['Absolute Time [s]'].tolist() == [
        start + pd.Timedelta(seconds=n) for n in [0, 10, 20]
    ]
    saved = tmp_path / 'processed' / 'synthetic_cleaned_data.parquet'
    assert_frame_equal(pd.read_parquet(saved), result)
    assert source.read_bytes() == original
    split_extension = '.csv' if extension == '.xlsx' else extension
    assert (tmp_path / 'pre_processed' /
            ('synthetic_data' + split_extension)).exists()
