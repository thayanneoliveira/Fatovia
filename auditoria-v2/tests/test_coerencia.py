"""Testes sintéticos dos cruzamentos públicos (nenhum dado pessoal)."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"auditar_coerencia_2026.py"
spec=importlib.util.spec_from_file_location("coerencia",SCRIPT)
coerencia=importlib.util.module_from_spec(spec)
spec.loader.exec_module(coerencia)

K=("AC","1234","1","2")
Z1=(1,"AC","1234","1")
Z2=(2,"AC","1234","1")
A=(100,90,10)
B=(100,80,20)

class CrossTests(unittest.TestCase):
    def test_equal_sources(self):
        stats,rows=coerencia.reconcile({K:A},{1:{K:B},2:{K:A}},
                                      {Z1:B,Z2:A},{K:(100,80,0)},"AC")
        self.assertEqual(stats.get("BU_e_detalhe_2T_divergentes",0),0)
        self.assertEqual(stats.get("zonas_ELO_e_detalhe_diferentes",0),0)
        self.assertEqual(stats["excecoes_documentais"],0)
        self.assertEqual(stats["secoes_com_dois_turnos"],1)
        self.assertEqual(stats["secoes_comparecimento_distinto_entre_turnos"],1)
    def test_bu_mismatch_is_documentary_not_fraud(self):
        stats,rows=coerencia.reconcile({K:A},{1:{K:B},2:{K:B}},
                                      {Z1:B,Z2:B},{K:(100,80,0)},"AC")
        self.assertEqual(stats["BU_e_detalhe_2T_divergentes"],1)
        self.assertEqual(rows[0]["status"],"DIFERENCA_DOCUMENTAL_A_EXPLICAR")
        self.assertEqual(rows[0]["tipo"],"BU_VS_DETALHE_2T")
    def test_missing_elo_is_not_zero_difference(self):
        stats,rows=coerencia.reconcile({K:A},{1:{K:B},2:{K:A}},
                                      {},{K:(100,80,0)},"AC")
        self.assertEqual(stats["zonas_sem_cobertura_ambos"],2)
        self.assertTrue(any(x["tipo"]=="AUSENCIA_DE_FONTE_ZONA" for x in rows))
    def test_aptos_balance_is_flagged_with_explicit_caveat(self):
        stats,rows=coerencia.reconcile({K:(100,92,5)},{1:{K:B},2:{K:A}},
                                      {Z1:B,Z2:A},{K:(100,70,0)},"AC")
        self.assertEqual(stats["desbalanceamento_bu"],1)
        self.assertTrue(any(x["status"]=="VERIFICAR_REGRAS_DE_AGREGACAO_E_TTE" for x in rows))
    def test_profile_biometrics_not_individual(self):
        stats,rows=coerencia.reconcile({K:A},{1:{K:B},2:{K:A}},
                                      {Z1:B,Z2:A},{K:(100,120,0)},"AC")
        self.assertEqual(stats["secoes_biometria_maior_que_eleitorado_perfil"],1)
        self.assertFalse(any("CPF" in str(x) for x in rows))

if __name__=="__main__":
    unittest.main()
