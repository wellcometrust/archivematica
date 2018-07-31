# -*- coding: utf8
import os
import sys

from lxml import etree
import metsrw

from main import models
from job import Job


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(THIS_DIR, 'fixtures')
sys.path.append(os.path.abspath(os.path.join(THIS_DIR, '../lib/clientScripts')))
import archivematicaCreateMETSReingest
import create_mets_v2

NSMAP = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'dcterms': 'http://purl.org/dc/terms/',
    'mets': 'http://www.loc.gov/METS/',
    'premis': 'info:lc/xmlns/premis-v2',
    'xlink': 'http://www.w3.org/1999/xlink',
}


def test_stuff(mocker):
    mocker.patch('main.models.Event.objects.filter',
                 return_value='monkeys')
    mets = metsrw.METSDocument.fromfile(
        os.path.join(FIXTURES_DIR, 'mets_no_namespaces.xml'))
    assert len(mets.tree.findall(
        'mets:amdSec[@ID="amdSec_2"]//mets:mdWrap[@MDTYPE="PREMIS:OBJECT"]',
        namespaces=NSMAP)) == 1
    sip_uuid = 'bdcb560d-7ddd-4c13-8040-1e565b4eddff'
    mets = archivematicaCreateMETSReingest.update_object(
        Job("stub", "stub", []), mets, sip_uuid)
    models.Event.objects.filter.assert_not_called()
    print(mets)
    print(type(mets))
