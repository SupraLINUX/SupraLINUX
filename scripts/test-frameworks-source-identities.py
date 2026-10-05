#!/usr/bin/env python3
"""Reject unbound legacy source identities without rewriting historical nodes."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inputs',ROOT/'scripts/frameworks-revalidation-inputs.py')
inputs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inputs)


class SourceIdentities(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.original_root = inputs.ROOT
        inputs.ROOT = self.root
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(setattr,inputs,'ROOT',self.original_root)
        self.registry = json.loads((ROOT/'manifests/frameworks-source-identities.json').read_text())
        self.nodes = json.loads((ROOT/'manifests/kde-dag.json').read_text())['nodes']
        for identity in self.registry['nodes'].values():
            source = ROOT/identity['manifest_path']
            destination = self.root/identity['manifest_path']
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(source.read_bytes())
        self.save()

    def save(self):
        (self.root/'manifests/frameworks-source-identities.json').write_text(json.dumps(self.registry))

    def test_exact_closed_sources_and_unchanged_nodes(self):
        before = copy.deepcopy(self.nodes)
        for node in ['kirigami','kcmutils']:
            self.assertEqual(inputs.source_package(node,self.nodes[node]),'kf6-'+node)
            self.assertNotIn('source_package',self.nodes[node])
        self.assertEqual(before,self.nodes)

    def test_existing_source_needs_no_completion(self):
        self.assertEqual(inputs.source_package('kcoreaddons',self.nodes['kcoreaddons']),'kf6-kcoreaddons')

    def test_changed_closed_manifest(self):
        path = self.root/self.registry['nodes']['kirigami']['manifest_path']
        path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaises(AssertionError):inputs.source_package('kirigami',self.nodes['kirigami'])

    def test_different_source(self):
        self.registry['nodes']['kirigami']['source_package']='unreviewed-provider'
        self.save()
        with self.assertRaises(AssertionError):inputs.source_package('kirigami',self.nodes['kirigami'])

    def test_superseded_version(self):
        node=copy.deepcopy(self.nodes['kcmutils'])
        node['package_version']='6.30.0-0supralinux4'
        with self.assertRaises(AssertionError):inputs.source_package('kcmutils',node)

    def test_different_artifact_and_upstream(self):
        for field,value in [('artifact_sha256','0'*64),('artifact_id',1)]:
            original=self.registry['nodes']['kcmutils'][field]
            self.registry['nodes']['kcmutils'][field]=value
            self.save()
            with self.assertRaises(AssertionError):inputs.source_package('kcmutils',self.nodes['kcmutils'])
            self.registry['nodes']['kcmutils'][field]=original
        self.save()
        node=copy.deepcopy(self.nodes['kcmutils'])
        node['source_sha256']='0'*64
        with self.assertRaises(AssertionError):inputs.source_package('kcmutils',node)

    def test_ineligible_or_different_binary_scope(self):
        node=copy.deepcopy(self.nodes['kirigami'])
        node['state']='FAIL'
        with self.assertRaises(AssertionError):inputs.source_package('kirigami',node)
        node=copy.deepcopy(self.nodes['kirigami'])
        node['binary_packages'].pop()
        with self.assertRaises(AssertionError):inputs.source_package('kirigami',node)

    def test_missing_identity_and_escaping_path(self):
        self.registry['nodes']['kirigami']['manifest_path']='../../outside.json'
        self.save()
        with self.assertRaises(AssertionError):inputs.source_package('kirigami',self.nodes['kirigami'])
        with self.assertRaises(KeyError):inputs.source_package('unreviewed',{'state':'PASS'})


if __name__=='__main__':unittest.main()
