from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_sync_events_command_success(monkeypatch):
    """Verifica que la comanda 'sync_events' s'executa correctament

    i crida la tasca de sincronització, mostrant els missatges pel stdout.
    """

    # 1. Creem un mock de la tasca perquè retorni un text controlat i conegut
    def fake_sync_events_task():
        return "Sincronització completa: 5 creats, 2 actualitzats."

    # Substituïm la funció real per la nostra simulada dins del mòdul de la comanda
    monkeypatch.setattr(
        "api.management.commands.sync_events.sync_events_task", fake_sync_events_task
    )

    # 2. Utilitzem StringIO per capturar tot el text que la comanda escrigui a la terminal
    out = StringIO()

    # 3. Executem la comanda passant-li l'argument stdout per desviar la sortida de text
    call_command("sync_events", stdout=out)

    # 4. Recuperem el text capturat
    output_text = out.getvalue()

    # 5. Assertions: Verifiquem que surten tant el missatge d'inici com el resultat del mock
    assert "Iniciant la sincronització d'esdeveniments..." in output_text
    assert "Sincronització completa: 5 creats, 2 actualitzats." in output_text


@pytest.mark.django_db
def test_sync_events_command_handles_error(monkeypatch):
    """Verifica que si la tasca interna falla i llança una excepció,

    la comanda propaga l'error i no emmascara fallades crítiques.
    """

    # Simulem un error catastròfic (per exemple, un tall de connexió amb l'API externa)
    def fake_failing_task():
        raise Exception("Error de connexió amb el servidor extern")

    monkeypatch.setattr(
        "api.management.commands.sync_events.sync_events_task", fake_failing_task
    )

    out = StringIO()

    # Comprovem que en executar la comanda, aquesta peta amb l'excepció esperada
    with pytest.raises(Exception) as exc_info:
        call_command("sync_events", stdout=out)

    assert "Error de connexió amb el servidor extern" in str(exc_info.value)
