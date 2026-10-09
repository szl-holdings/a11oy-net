#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed contract for the current source-bound SZL Frontier proof record."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FR=ROOT/'estate'/'szl-frontier'
PAGE=FR/'index.html'; RECORD=FR/'alignment.json'; OBS=FR/'frontier-operational-37915819258.json'; BROWSER=FR/'live-browser-2026-10-09.json'; ESTATE=FR/'estate-release-train-34297559945.json'
SOURCE='f2eaf02a3f506e3220c233180cbddc6e66077c08'; PREVIOUS='1723045ecf5b06fd9a5e80a759ff22ea9804885d'; HEAD='435984365616bda3fd5062e94c921efd8a06ef8c'; TREE='a9c0e3c3a7475b89c426543f22d857fb37fbd88b'; SPACE='abd201876ee210b3c31b05bdf57faedef3604cd1'; PRODUCT_SOURCE='a62067cd22cbda6583533cdf6f447e859ba0b0a9'
SHA40=re.compile(r'^[0-9a-f]{40}$'); SHA256=re.compile(r'^[0-9a-f]{64}$')
def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def check()->None:
    for p in (PAGE,RECORD,OBS,BROWSER,ESTATE): assert p.is_file(), f'missing {p}'
    record=json.loads(RECORD.read_text(encoding='utf-8')); obs=json.loads(OBS.read_text(encoding='utf-8')); browser=json.loads(BROWSER.read_text(encoding='utf-8')); estate=json.loads(ESTATE.read_text(encoding='utf-8'))
    chain=['GitHub','Hugging Face','a-11-oy.com','a11oy.net']
    assert record['schema']=='szl.proof.frontier-alignment.v1' and record['authorityChain']==chain
    assert obs['schema']=='szl.proof.frontier-operational-observation.v1' and obs['authorityChain']==chain
    assert estate['schema']=='szl.proof.frontier-estate-release-observation.v1'
    assert record['source']=={'repository':'szl-holdings/szl-frontier','revision':SOURCE,'previousRevision':PREVIOUS,'state':'EXACT_AT_OBSERVATION'}
    assert all(SHA40.fullmatch(x) for x in (SOURCE,PREVIOUS,HEAD,TREE,SPACE,PRODUCT_SOURCE))
    src=obs['source']; assert src['pullRequest']==242 and src['baseRevision']==PREVIOUS and src['headRevision']==HEAD and src['mergeRevision']==SOURCE and src['tree']==TREE and src['signatureVerified'] is True
    assert src['softwarePlane']=='OPERATIONAL' and src['productionDisposition']=='HOLD' and src['productionAuthorization'] is False
    runs=obs['github']['postMergeRuns']; assert len(runs)==6 and all(r['conclusion']=='success' for r in runs) and obs['github']['allPostMergeSuccessful'] is True
    hub=record['huggingFace']; assert hub['spaceRepositoryRevision']==SPACE and hub['runtimeDeploymentSourceRevision']==SOURCE and hub['runtimeStage']=='RUNNING' and hub['syncWorkflowRun']==37915819258 and hub['syncWorkflowJob']==113771608026 and hub['witness']=='PASS'
    assert hub['runtimeDeploymentSha256']=='ea4df6392e3ee7447ecdb7412d77abeb9a07bcd4b4aad96aa64fdb9d04b1806e' and hub['runtimeHealthSha256']=='17d480fe82a128998c43514a045481855c9bda6ec7ba2fc4b7875e13a0c970cf' and hub['publisherReceiptSha256']=='5700a10aa61d0de8bc998c45ed16977fb8d87255b96128245d1e4a1c6b1b3cdc' and hub['browserReceiptSha256']=='5fff0bef60382600b0bf46ea22e4fa8ffde31b3bfbdbe5e07c05f301fcf2797e'
    oh=obs['huggingFace']; assert oh['spaceRepositoryRevision']==SPACE and oh['runtimeRepositoryRevision']==SPACE and oh['sourceRevision']==SOURCE and oh['runtimeStage']=='RUNNING' and oh['publishedFiles']==599
    assert oh['publisherReceiptArtifactId']==11609173699 and oh['publisherReceiptSha256']=='5700a10aa61d0de8bc998c45ed16977fb8d87255b96128245d1e4a1c6b1b3cdc'
    assert oh['companionProjection']['state']=='VERIFIED_NO_CHANGE' and oh['companionProjection']['newCommit'] is False and oh['companionProjection']['receiptSha256']=='545db3a37045bd3244ef7185729cfbe18cb23f13180010b71b099dc7fa697694'
    health=obs['runtime']['health']; assert health['httpStatus']==200 and health['operational'] is True and health['softwareState']=='OPERATIONAL' and health['productionDisposition']=='HOLD' and health['productionAuthorization'] is False and health['runtimeVerified'] is False
    dep=obs['runtime']['deployment']; assert dep['httpStatus']==200 and dep['sourceRevision']==SOURCE and dep['sourceIdentityVerified'] is True
    assert digest(BROWSER)=='5fff0bef60382600b0bf46ea22e4fa8ffde31b3bfbdbe5e07c05f301fcf2797e'
    expected={'journeys':8,'navFailures':0,'consoleErrors':0,'pageErrors':0,'requestFailures':0,'httpErrors':0,'overflow':0,'effectiveUndersized':0,'focusFailures':0,'missingMain':0}
    assert browser['sourceRevision']==SOURCE and browser['providerRevision']==SPACE and browser['totals']==expected
    b=obs['runtime']['browser']; assert b['verdict']=='PASS' and all(b[k]==v for k,v in expected.items())
    product=obs['productProjection']; assert product['httpStatus']==200 and product['productSourceRevision']==PRODUCT_SOURCE and product['relationship']=='SEPARATE_A11OY_UNIFIED_SHOWCASE' and product['exactFrontierByteParity']=='NOT_CLAIMED' and product['productionAuthorization'] is False
    current=record['latestFrontierOperationalObservation']; assert current['record']=='./frontier-operational-37915819258.json' and current['sourceRevision']==SOURCE and current['huggingFaceSpaceRepositoryRevision']==SPACE and current['runtimeSourceRevision']==SOURCE and current['sourceRuntimeParity']=='MATCH' and current['softwareState']=='OPERATIONAL' and current['runtimeVerified'] is False and current['productionAuthorization'] is False and current['browserAcceptance']=='PASS'
    assert record['product']['witnessScope']=='HISTORICAL_FRONTIER_NOW_SUMMARY' and 'preserved historical' in record['product']['note']
    assert record['latestEstateObservation']['status']=='PRESERVED_HISTORICAL_A11OY_ESTATE_OBSERVATION' and estate['productionDisposition']=='HOLD' and estate['automaticPromotion'] is False
    assert record['measuredEvidence']['glm53FlashVsKhipu']['promotionEffect']=='NONE'
    assert record['proof']['state']=='CURRENT_FRONTIER_SOFTWARE_OPERATIONAL_SOURCE_HF_EXACT_PRODUCT_PROJECTION_SEPARATE_PRODUCTION_HOLD'
    assert record['overall']=={'state':'FRONTIER_SOFTWARE_OPERATIONAL_SOURCE_HF_EXACT_BROWSER_PASS_PRODUCT_PROJECTION_SEPARATE_PRODUCTION_HOLD','softwarePlaneOperational':True,'runtimeVerified':False,'productionDisposition':'HOLD','productionAuthorization':False,'automaticPromotion':False}
    page=PAGE.read_text(encoding='utf-8')
    for value in (SOURCE,PREVIOUS,TREE,SPACE,'ea4df6392e3ee7447ecdb7412d77abeb9a07bcd4b4aad96aa64fdb9d04b1806e','17d480fe82a128998c43514a045481855c9bda6ec7ba2fc4b7875e13a0c970cf','5fff0bef60382600b0bf46ea22e4fa8ffde31b3bfbdbe5e07c05f301fcf2797e',PRODUCT_SOURCE): assert value in page
    for link in ('./alignment.json','./frontier-operational-37915819258.json','./live-browser-2026-10-09.json','./estate-release-train-34297559945.json'): assert f'href="{link}"' in page
    for phrase in ('SOFTWARE OPERATIONAL','PRODUCTION HOLD','runtimeVerified=false','NOT_CLAIMED','No ATO','Conjecture 1'): assert phrase in page
    forbidden=('fully production ready','autonomous production authority granted','model quality verified')
    assert not any(x in page.lower() for x in forbidden)
    print('OK: Frontier exact source/HF/browser evidence is current; software is OPERATIONAL and production remains HOLD.')
if __name__=='__main__': check()
