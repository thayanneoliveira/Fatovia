import unittest, tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from fatovia import multiformat as mf
from fatovia import publisher as pub

NOW=datetime.fromisoformat("2026-11-18T14:12:00-03:00")
CFG={"enabled":True,"token":"fake","ig_id":"123","base":"https://graph.instagram.com/v25.0"}
REEL={"format":"reel","id":"reel:creche-v5","version":"1234567890abcd","status":"ready","caption":"Exemplo ficticio de cidadania. Consulte as fontes na legenda.\nID editorial: reel:creche-v5/1234567890abcd","voice":"Santa-R-1.0","visual_revision":"V5","video_path":"docs/media/reels/creche.mp4"}
class FakeMeta:
    def __init__(self,existing=None):
        self.calls=[];self.found=existing
    def account(self):return {"username":"fato.via"}
    def existing(self,item):return self.found
    def create(self,data):self.calls.append(("create",data));return "container"
    def ready(self,c):self.calls.append(("ready",c))
    def publish(self,c):self.calls.append(("publish",c));return "media"
    def permalink(self,m):return "https://www.instagram.com/reel/mock/"
class MixedTests(unittest.TestCase):
    def test_migration(self):
        self.assertTrue(mf.mode(NOW));self.assertFalse(mf.mode(NOW.replace(day=17)))
    def test_transition_requires_review(self):
        report={"evaluation_ready":True,"issues":[],"pilot_id":"p","publications":[{"media_id":"123"}]}
        approval={"authorized":True,"pilot_id":"p","reviewed_media_ids":["123"],"review_reference":"review-1"}
        with patch("fatovia.pilot_report.build",return_value=report),patch.object(Path,"read_text",return_value="{}"):
            self.assertFalse(mf.transition_authorized({},NOW,{}))
            self.assertTrue(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
            self.assertFalse(mf.transition_authorized({},NOW,{"pilot_transition":{**approval,"reviewed_media_ids":[]}}))
            report["issues"]=["pilot_total_exceeded"]
            self.assertFalse(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
            report["issues"]=[]
            report["evaluation_ready"]=False
            self.assertFalse(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
    def test_incident_closure_never_auto_approves(self):
        import json
        report={"evaluation_ready":False,"issues":["pilot_total_exceeded"],
                "pilot_id":"p","published":1,"publications":[{"media_id":"123"}]}
        approval={"authorized":True,"pilot_id":"p","reviewed_media_ids":["123"],"review_reference":"review-1"}
        closure={"pilot_id":"p","closure_type":"closed_with_incident","incident_preserved":True,
                 "legacy_history_must_remain":True,"observed_pilot_count":1,
                 "issues":["pilot_total_exceeded"],"production_transition_authorized":False,
                 "reconciliation":{"status":"pending_live_meta_verification","account_id_verified":False,"media_ids_verified":[]}}
        def read(path,**kwargs):
            return json.dumps(closure) if "closure" in str(path) else "{}"
        with patch("fatovia.pilot_report.build",return_value=report),patch.object(Path,"read_text",autospec=True,side_effect=read):
            self.assertFalse(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
            closure["production_transition_authorized"]=True
            self.assertFalse(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
            closure["reconciliation"]={"status":"verified_against_live_meta","account_id_verified":True,"media_ids_verified":["123"]}
            self.assertTrue(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
            closure["issues"]=[]
            self.assertFalse(mf.transition_authorized({},NOW,{"pilot_transition":approval}))
    def test_transition_missing_policy_fails_closed(self):
        with patch.object(Path,"read_text",side_effect=OSError):
            self.assertFalse(mf.transition_authorized({},NOW,{}))
    def test_unauthorized_transition_blocks_both_formats(self):
        with patch.object(mf,"transition_authorized",return_value=False), patch.object(mf,"quota",side_effect=AssertionError("quota must not be reached")):
            self.assertFalse(mf.allowed({"published":[]},REEL,NOW,{}))
            self.assertFalse(mf.allowed({"published":[]},{"format":"carousel"},NOW,{}))
    def test_slots(self):
        self.assertEqual([mf.slot(NOW.replace(hour=h)) for h in range(8,21,3)],["carousel","carousel","reel","carousel","carousel"])
        self.assertIsNone(mf.slot(NOW.replace(minute=46)))
    def test_daily_limits(self):
        s={"published":[{"published_at":NOW.replace(hour=h).isoformat()} for h in (8,11,17,20)]}
        self.assertFalse(mf.quota(s,NOW.replace(hour=20),"carousel"))
        s={"published":[{"published_at":NOW.replace(hour=8).isoformat(),"format":"reel"}]}
        self.assertFalse(mf.quota(s,NOW,"reel"))
    def test_min_gap(self):
        self.assertFalse(mf.quota({"published":[{"published_at":NOW.replace(hour=11,minute=35).isoformat()}]},NOW,"reel"))
    def test_blackout(self):
        self.assertFalse(mf.quota({"published":[],"blackout_dates":["2026-11-18"]},NOW,"reel"))
    def test_owner_scope_is_required_and_exclusions_win(self):
        policy={"owner_per_content_authorization":{
            "decision":"authorized_by_owner_pending_operational_validation",
            "max_spend_brl":0,"daily_caps":mf.CAPS,
            "carousel_ids":["camara:2653947"],"reel_ids":["reel:inflacao-precos-20261118"],
            "excluded_ids":["camara:2654163"]}}
        self.assertTrue(mf.owner_authorized({"id":"camara:2653947"},policy))
        self.assertTrue(mf.owner_authorized({"id":"reel:inflacao-precos-20261118","format":"reel"},policy))
        self.assertFalse(mf.owner_authorized({"id":"camara:2654163"},policy))
        self.assertFalse(mf.owner_authorized({"id":"camara:other"},policy))
        self.assertFalse(mf.owner_authorized({"id":"camara:2653947"},{**policy,"owner_per_content_authorization":{}}))
        with patch.object(mf,"transition_authorized",side_effect=AssertionError("must fail before transition")):
            self.assertFalse(mf.allowed({},{"id":"camara:other"},NOW,policy))
    def test_missing_logo_fails(self):
        p={"status":"prepared_guarded","daily_caps":mf.CAPS,"max_spend_brl":0,"start_date":"2026-11-18","approved_logo":{"path":"assets/fatovia-approved.png","sha256":None},"approved_items":[]}
        self.assertFalse(mf.allowed({"published":[]},REEL,NOW,p))
    def test_approved_status_still_requires_transition(self):
        p={"status":"approved","daily_caps":mf.CAPS,"max_spend_brl":0,
           "start_date":"2026-11-18","approved_logo":{"path":"assets/fatovia-approved.png","sha256":None},
           "approved_items":[]}
        with patch.object(mf,"transition_authorized",return_value=False):
            self.assertFalse(mf.allowed({"published":[]},REEL,NOW,p))
    def test_approved_status_still_requires_logo(self):
        p={"status":"approved","daily_caps":mf.CAPS,"max_spend_brl":0,
           "start_date":"2026-11-18","approved_logo":{"path":"assets/fatovia-approved.png","sha256":None},
           "approved_items":[]}
        with patch.object(mf,"transition_authorized",return_value=True):
            self.assertFalse(mf.allowed({"published":[]},REEL,NOW,p))
    def test_malformed_policy_fails(self):
        self.assertFalse(mf.allowed({"published":[]},REEL,NOW,{}))
    def test_video_path_traversal(self):
        with self.assertRaises(ValueError):mf.reel_url({**REEL,"video_path":"docs/media/reels/../x.mp4"})
    def test_reel_qualified(self):
        self.assertTrue(mf.reel_qualified(REEL));self.assertFalse(mf.reel_qualified({**REEL,"voice":"other"}))
    def test_prepare_deliver_reel_mock(self):
        state={"pending":[],"reel_pending":[dict(REEL)],"published":[]}
        client=FakeMeta()
        with tempfile.TemporaryDirectory() as t,patch.object(pub,"STATE_PATH",Path(t)/"state.json"),patch.object(mf,"allowed",return_value=True),patch.object(mf,"verify_reel_hosted",return_value=True):
            self.assertEqual(pub.prepare(state,NOW,CFG)["action"],"prepared")
            self.assertEqual(pub.deliver(state,NOW,CFG,client=client)["action"],"published")
        self.assertEqual(client.calls[0][1]["media_type"],"REELS")
        self.assertEqual(state["published"][0]["format"],"reel");self.assertEqual(state["reel_pending"],[])
        self.assertEqual([x[0] for x in client.calls],["create","ready","publish"])
    def test_reel_hosting_blocks_posts(self):
        state={"pending":[],"reel_pending":[dict(REEL)],"published":[]}
        client=FakeMeta()
        with tempfile.TemporaryDirectory() as t,patch.object(pub,"STATE_PATH",Path(t)/"state.json"),patch.object(mf,"allowed",return_value=True),patch.object(mf,"verify_reel_hosted",return_value=False):
            pub.prepare(state,NOW,CFG)
            with self.assertRaises(pub.PublicationError):pub.deliver(state,NOW,CFG,client=client)
        self.assertFalse(client.calls)
    def test_reconcile_does_not_post(self):
        state={"pending":[],"reel_pending":[dict(REEL)],"published":[]}
        client=FakeMeta({"id":"media","permalink":"https://www.instagram.com/reel/mock/"})
        with tempfile.TemporaryDirectory() as t,patch.object(pub,"STATE_PATH",Path(t)/"state.json"),patch.object(mf,"allowed",return_value=True):
            pub.prepare(state,NOW,CFG);self.assertEqual(pub.reconcile(state,NOW,CFG,client=client)["action"],"recovered")
        self.assertFalse(client.calls)
if __name__=="__main__":unittest.main()
