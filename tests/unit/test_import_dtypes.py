"""Preserve source identifiers without weakening measurement validation."""
import csv
from io import StringIO
from pathlib import Path

import openpyxl
import pandas as pd
import pytest
from pandas.api.types import is_numeric_dtype
from pandas.testing import assert_frame_equal

from pbdp import Parser


@pytest.mark.parametrize('extension', ['.csv', '.txt', '.mpt', '.DTA', '.xlsx'])
def test_import_dtypes_preserve_text_and_normalize_measurements(tmp_path, extension):
    source = tmp_path / ('cells' + extension)
    rows = [
        ['time/s', 'I/mA', 'Ecell/V', 'Cell ID', 'Batch', 'Comment'],
        ['0', '1000', '3.7', '0007', '001', 'ready'],
        ['10', '-500', '3.6', '0042', 'batch-A', 'retest'],
        ['20', '0', '3.6', '0009', '003', ''],
    ]
    if extension == '.xlsx':
        workbook = openpyxl.Workbook()
        for row in rows:
            workbook.active.append(row)
        workbook.save(source)
        workbook.close()
    else:
        stream = StringIO(newline='')
        delimiter = ',' if extension == '.csv' else '\t'
        csv.writer(stream, delimiter=delimiter).writerows(rows)
        source.write_text(stream.getvalue(), encoding='utf-8')

    result = Parser().data_importer(
        source, file_type='parquet',
        dtype={'Cell ID': str, 'Batch': 'string', 'Comment': 'string',
               'time/s': str, 'I/mA': str, 'Ecell/V': str},
    )

    assert result['Cell ID'].tolist() == ['0007', '0042', '0009']
    assert result['Batch'].tolist() == ['001', 'batch-A', '003']
    assert result['Comment'].iloc[:2].tolist() == ['ready', 'retest']
    assert pd.isna(result['Comment'].iloc[2])
    assert result['Time [s]'].tolist() == [0, 10, 20]
    assert result['Current [A]'].tolist() == pytest.approx([1, -.5, 0])
    assert result['Voltage [V]'].tolist() == pytest.approx([3.7, 3.6, 3.6])
    for name in ['Time [s]', 'Current [A]', 'Voltage [V]']:
        assert is_numeric_dtype(result[name])
    saved = tmp_path / 'processed' / 'cells_cleaned_data.parquet'
    assert_frame_equal(pd.read_parquet(saved), result)


def test_csv_export_keeps_identifier_characters_and_positional_arguments(tmp_path):
    source = tmp_path / 'cells.csv'
    source.write_text('time/s,I/mA,Ecell/V,Cell ID\n0,1000,3.7,0007\n',
                      encoding='utf-8')

    result = Parser().data_importer(
        source, '', 'csv', 'save', '', '', {'Cell ID': str}
    )

    saved = tmp_path / 'processed' / 'cells_cleaned_data.csv'
    with saved.open(newline='', encoding='utf-8') as stream:
        assert list(csv.DictReader(stream))[0]['Cell ID'] == '0007'
    restored = pd.read_csv(saved, dtype={'Cell ID': str})
    assert_frame_equal(restored, result)


def test_direct_reader_accepts_raw_header_dtype_mapping():
    data = b'Cell ID,Optional,Current\n0007,1,1000\n0042,remark,-500\n'
    result = Parser().read_data_to_pandas(
        data, Path('cells.csv'), 'utf-8', {'Cell ID': str, 'Optional': 'string'}
    )

    assert result['Cell ID'].tolist() == ['0007', '0042']
    assert result['Optional'].tolist() == ['1', 'remark']
    assert result['Current'].tolist() == [1000, -500]
    assert is_numeric_dtype(result['Current'])


def test_import_without_dtype_keeps_inference_and_optional_text(tmp_path):
    source = tmp_path / 'cells.csv'
    source.write_text(
        'time/s,I/mA,Ecell/V,Cell ID,Comment\n'
        '0,1000,3.7,0007,ready\n10,-500,3.6,0042,retest\n',
        encoding='utf-8',
    )
    result = Parser().data_importer(source, save_option='none')

    assert result['Cell ID'].tolist() == [7, 42]
    assert result['Comment'].tolist() == ['ready', 'retest']
    assert result['Current [A]'].tolist() == pytest.approx([1, -.5])


@pytest.mark.parametrize('field', ['time/s', 'I/mA', 'Ecell/V'])
def test_text_dtype_does_not_allow_invalid_required_measurements(tmp_path, field):
    source = tmp_path / 'invalid.csv'
    header = ['time/s', 'I/mA', 'Ecell/V', 'Cell ID']
    invalid = ['10', '500', '3.6', '0042']
    invalid[header.index(field)] = 'invalid'
    stream = StringIO(newline='')
    csv.writer(stream).writerows([
        header, ['0', '1000', '3.7', '0007'], invalid,
    ])
    source.write_text(stream.getvalue(), encoding='utf-8')

    with pytest.raises(ValueError, match='finite numbers'):
        Parser().data_importer(source, dtype={name: str for name in header})
    assert not (tmp_path / 'processed').exists()
