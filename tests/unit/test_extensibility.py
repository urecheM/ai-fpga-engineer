from __future__ import annotations

from hdleval.optimization.objectives import DesignPoint, Objective, pareto_frontier, score_design
from hdleval.orchestration.dag import DAG, Node
from hdleval.plugins import PluginKind, registry
from hdleval.rag.retriever import Document, KnowledgeRetriever
from hdleval.repair.diagnose import diagnose


def test_dag_runs_in_order_and_caches():
    dag = DAG()
    dag.add(Node("a", lambda i: 1))
    dag.add(Node("b", lambda i: i["a"] + 1, deps=["a"]))
    r1 = dag.run()
    assert r1["b"].value == 2 and not r1["b"].cached
    r2 = dag.run()
    assert r2["b"].cached


def test_dag_detects_cycles():
    dag = DAG()
    dag.add(Node("a", lambda i: 1, deps=["b"]))
    dag.add(Node("b", lambda i: 1, deps=["a"]))
    try:
        dag.run()
    except ValueError as e:
        assert "cycle" in str(e)
    else:
        raise AssertionError("cycle not detected")


def test_pareto_frontier():
    pts = [
        DesignPoint("x", 100, 200, 5),
        DesignPoint("y", 120, 180, 6),
        DesignPoint("z", 90, 210, 4),
    ]
    front = pareto_frontier(pts)
    assert any(p.name == "z" for p in front)
    assert score_design(pts[0], Objective.TIMING) == 200


def test_plugin_registry():
    @registry.register(PluginKind.DOC_GENERATOR, "dummy")
    def _f():
        return "ok"

    assert "dummy" in registry.names(PluginKind.DOC_GENERATOR)


def test_rag_retrieval():
    docs = [
        Document("d1", "spi master mode 0 sclk mosi miso"),
        Document("d2", "uart transmitter start stop baud"),
    ]
    r = KnowledgeRetriever(docs)
    hits = r.retrieve("spi sclk", k=1)
    assert hits and hits[0].id == "d1"


def test_repair_diagnosis():
    d = diagnose("syntax error near ';'")
    assert d.failure_class == "syntax_error" and d.corrective_hint
