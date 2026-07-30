import unittest
from storycraft.llm_responses import candidate_response, review_response
from storycraft.series_contracts import ContractError
class LlmResponsesTests(unittest.TestCase):
 def test_candidate_and_review_closed_schemas(self):
  self.assertEqual(candidate_response({'schema_version':1,'artifact_kind':'initial-design','payload':{}},'initial-design')['payload'],{})
  self.assertEqual(review_response({'schema_version':'review-response-v1','decision':'pass','issues':[]})['decision'],'pass')
 def test_rejects_mismatch(self):
  with self.assertRaises(ContractError): candidate_response({'schema_version':1,'artifact_kind':'series-plan','payload':{}},'initial-design')
  with self.assertRaises(ContractError): review_response({'schema_version':'review-response-v1','decision':'pass','issues':[{}]})
