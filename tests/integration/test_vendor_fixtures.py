"""Small synthetic exports using headers from the bundled vendor examples."""
import pytest

from pbdp import Parser


@pytest.mark.parametrize('name,content,expected_time', [
    ('digatron.csv',
     'Step,Status,Prog Time,Voltage,Current,AhAccu\n'
     '[],[],[s],[V],[A],[Ah]\n'
     '1,1,0,3.5,1,0\n20,1,10,3.6,1,0.0027777778\n', [0, 10]),
    ('maccor.csv',
     'Rec,Step,TestTime,Current [A],Voltage [V],Cap. [Ah]\n'
     '0,1,00:00:00,1,3.5,0\n1,2,00:00:10,1,3.6,0.0027777778\n', [0, 10]),
    ('gamry.DTA',
     '\tPt\tT\tVf\tIm\tTemp\n'
     '\t#\ts\tV vs. Ref.\tA\tdeg C\n'
     '\t0\t0\t3.5\t1\t20\n\t1\t10\t3.6\t1\t21\n', [0, 10]),
    ('novonix.csv',
     'Date and Time,Cycle Number,Run Time (h),Current (A),Potential (V)\n'
     '2026-01-01 09:00:00,1,0,1,3.5\n'
     '2026-01-01 10:00:00,1,1,1,3.6\n', [0, 3600]),
    ('biologic.mpt',
     'time/s\t<I>/mA\tEcell/V\t(Q-Qo)/mA.h\n'
     '0\t1000\t3.5\t0\n10\t1000\t3.6\t2.7777778\n', [0, 10]),
])
def test_vendor_headers_and_units(tmp_path, name, content, expected_time):
    path = tmp_path / name
    path.write_text(content, encoding='utf-8')
    result = Parser().data_importer(path, save_option='none', state_option='yes')
    assert len(result) == 2
    assert result['Time [s]'].tolist() == pytest.approx(expected_time)
    assert result['Current [A]'].tolist() == pytest.approx([1, 1])
    assert result['Voltage [V]'].tolist() == pytest.approx([3.5, 3.6])
    assert result['Battery State'].tolist() == ['charging', 'charging']
    assert path.read_text(encoding='utf-8') == content
    if name == 'novonix.csv':
        assert 'Date and Time' in result.columns


def test_eis_import_without_elapsed_time(tmp_path):
    path = tmp_path / 'spectrum.mpt'
    path.write_text('freq/Hz\tRe(Z)/Ohm\tIm(Z)/Ohm\n100\t0.1\t-0.02\n',
                    encoding='utf-8')
    result = Parser().data_importer(path, save_option='none')
    assert result['freq [Hz]'].tolist() == [100]
    assert result['ReZ [Ohm]'].tolist() == pytest.approx([0.1])
    assert result['ImZ [Ohm]'].tolist() == pytest.approx([-0.02])
