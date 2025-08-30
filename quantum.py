import os
from typing import Optional, List
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler

# Optional AWS Braket
_BRK = None
try:
    from braket.circuits import Circuit as BraketCircuit
    from braket.aws import AwsDevice, AwsDeviceType, AwsQuantumTask
    _BRK = True
except Exception:
    _BRK = False

def _ibm_service() -> Optional[QiskitRuntimeService]:
    token = os.getenv("IBM_QUANTUM_TOKEN")
    if not token:
        return None
    try:
        return QiskitRuntimeService(channel="ibm_quantum", token=token)
    except Exception:
        return None

def _simulate_counts(qc: QuantumCircuit, shots: int = 1024) -> dict:
    sim = AerSimulator()
    result = sim.run(qc, shots=shots).result()
    return result.get_counts()

def _format_counts(counts: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)) or "нет результатов"

def backends_info() -> str:
    info = ["⚛️ Доступные бэкенды:"]
    svc = _ibm_service()
    if svc:
        try:
            bks = [b.name for b in svc.backends(operational=True)]
            info.append("• IBM: " + (", ".join(bks[:10]) + (" ..." if len(bks) > 10 else "")))
        except Exception:
            info.append("• IBM: доступ есть, но список не получен")
    else:
        info.append("• IBM: ❌ нет токена")

    if _BRK and os.getenv("AWS_REGION"):
        try:
            # Список устройств (статический набор ARN известен на стороне AWS Braket документации; здесь укажем ключевые)
            devices = [
                "arn:aws:braket:::device/quantum-simulator/amazon/sv1",
                "arn:aws:braket:::device/quantum-simulator/amazon/tn1",
                # Реальные провайдеры доступны из консоли; перечислим часто используемые:
                "arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1",
                "arn:aws:braket:us-west-1::device/qpu/rigetti/Aspen-M-3",
                "arn:aws:braket:us-west-2::device/qpu/d-wave/Advantage_system6"
            ]
            info.append("• AWS Braket: " + ", ".join(devices[:5]))
        except Exception:
            info.append("• AWS Braket: модуль есть, но список не получен")
    else:
        info.append("• AWS Braket: ❌ не настроен")
    return "\n".join(info)

async def run_preset_circuit(kind: str, qubits: int) -> str:
    kind = kind.lower()
    if kind == "bell":
        qc = QuantumCircuit(2, 2)
        qc.h(0); qc.cx(0, 1); qc.measure([0,1], [0,1])
    elif kind == "ghz":
        qubits = max(3, qubits)
        qc = QuantumCircuit(qubits, qubits)
        qc.h(0)
        for i in range(qubits-1):
            qc.cx(i, i+1)
        qc.measure(range(qubits), range(qubits))
    elif kind == "qft":
        from qiskit.circuit.library import QFT
        qubits = max(2, qubits)
        qc = QuantumCircuit(qubits, qubits)
        qc.compose(QFT(num_qubits=qubits), inplace=True)
        qc.measure(range(qubits), range(qubits))
    else:
        return "Неизвестный пресет. Доступно: bell, ghz, qft."

    # Prefer IBM if available
    svc = _ibm_service()
    if svc:
        try:
            backend = svc.backends(simulator=False, operational=True)[0]
            sampler = Sampler(mode=backend)
            job = sampler.run([qc], shots=1024)
            res = job.result()
            counts = res[0].data.meas.get_counts()
            return f"🧪 IBM ({backend.name}):\n{_format_counts(counts)}"
        except Exception:
            pass

    # Fallback: local Aer
    counts = _simulate_counts(qc, shots=1024)
    return f"🧪 AerSimulator (local):\n{_format_counts(counts)}"

async def run_openqasm(qasm_text: str) -> str:
    from qiskit.qasm3 import loads as qasm3_loads
    try:
        qc = qasm3_loads(qasm_text)
    except Exception as e:
        return f"Ошибка парсинга OpenQASM 3.0: {e}"

    svc = _ibm_service()
    if svc:
        try:
            backend = svc.backends(simulator=False, operational=True)[0]
            sampler = Sampler(mode=backend)
            job = sampler.run([qc], shots=1024)
            res = job.result()
            counts = res[0].data.meas.get_counts()
            return f"🧪 IBM ({backend.name}):\n{_format_counts(counts)}"
        except Exception:
            pass

    counts = _simulate_counts(qc, shots=1024)
    return f"🧪 AerSimulator (local):\n{_format_counts(counts)}"
