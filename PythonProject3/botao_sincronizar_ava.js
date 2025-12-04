import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle, AlertCircle, Clock } from 'lucide-react';

/**
 * BotaoSincronizarAVA
 *
 * Botão para sincronizar manualmente com o AVA.
 * Mostra:
 * - Status da última sincronização
 * - Data/hora da última sync
 * - Progresso quando sincronizando
 * - Botão para iniciar nova sync
 */
const BotaoSincronizarAVA = () => {
  const [status, setStatus] = useState({
    sincronizando: false,
    tem_dados: false,
    ultima_sync: null,
    ultima_sync_formatada: null
  });

  const [mensagem, setMensagem] = useState('');
  const [erro, setErro] = useState('');

  // Busca status inicial e faz polling
  useEffect(() => {
    buscarStatus();

    // Polling a cada 5 segundos se estiver sincronizando
    const interval = setInterval(() => {
      if (status.sincronizando) {
        buscarStatus();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [status.sincronizando]);

  // Busca status do servidor
  const buscarStatus = async () => {
    try {
      const response = await fetch('/api/status_sync');

      if (response.ok) {
        const data = await response.json();
        setStatus(data);
        setErro('');
      } else {
        setErro('Erro ao verificar status');
      }
    } catch (error) {
      console.error('Erro ao buscar status:', error);
      setErro('Erro de conexão');
    }
  };

  // Inicia sincronização
  const iniciarSincronizacao = async () => {
    try {
      setMensagem('Iniciando sincronização...');
      setErro('');

      const response = await fetch('/api/sincronizar_ava', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (response.ok) {
        setMensagem(data.mensagem);
        setStatus(prev => ({ ...prev, sincronizando: true }));

        // Inicia polling
        setTimeout(buscarStatus, 2000);
      } else {
        setErro(data.erro || 'Erro ao iniciar sincronização');
        setMensagem('');
      }
    } catch (error) {
      console.error('Erro ao sincronizar:', error);
      setErro('Erro de conexão');
      setMensagem('');
    }
  };

  // Calcula tempo decorrido desde última sync
  const tempoDecorrido = () => {
    if (!status.ultima_sync) return null;

    const agora = new Date();
    const ultima = new Date(status.ultima_sync);
    const diff = agora - ultima;

    const minutos = Math.floor(diff / 60000);
    const horas = Math.floor(minutos / 60);
    const dias = Math.floor(horas / 24);

    if (dias > 0) {
      return `${dias} dia${dias > 1 ? 's' : ''} atrás`;
    } else if (horas > 0) {
      return `${horas} hora${horas > 1 ? 's' : ''} atrás`;
    } else if (minutos > 0) {
      return `${minutos} minuto${minutos > 1 ? 's' : ''} atrás`;
    } else {
      return 'Agora mesmo';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-w-md">
      {/* Título */}
      <div className="flex items-center gap-2 mb-4">
        <RefreshCw className="w-6 h-6 text-blue-600" />
        <h3 className="text-lg font-semibold text-gray-800">
          Sincronizar com AVA
        </h3>
      </div>

      {/* Status */}
      <div className="space-y-3 mb-4">
        {/* Última sincronização */}
        {status.tem_dados && status.ultima_sync_formatada && (
          <div className="flex items-start gap-2 text-sm">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-gray-700 font-medium">Última sincronização:</p>
              <p className="text-gray-600">{status.ultima_sync_formatada}</p>
              <p className="text-gray-500 text-xs">{tempoDecorrido()}</p>
            </div>
          </div>
        )}

        {/* Nunca sincronizou */}
        {!status.tem_dados && !status.sincronizando && (
          <div className="flex items-start gap-2 text-sm">
            <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-gray-700 font-medium">Primeira sincronização</p>
              <p className="text-gray-600">
                Clique em "Sincronizar" para carregar seus dados do AVA
              </p>
            </div>
          </div>
        )}

        {/* Sincronizando */}
        {status.sincronizando && (
          <div className="flex items-start gap-2 text-sm">
            <Clock className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5 animate-spin" />
            <div>
              <p className="text-gray-700 font-medium">Sincronizando...</p>
              <p className="text-gray-600">
                Este processo pode levar de 5 a 8 minutos
              </p>
              <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full animate-pulse w-2/3"></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mensagens */}
      {mensagem && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
          {mensagem}
        </div>
      )}

      {erro && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
          {erro}
        </div>
      )}

      {/* Botão de ação */}
      <button
        onClick={iniciarSincronizacao}
        disabled={status.sincronizando}
        className={`
          w-full py-3 px-4 rounded-lg font-medium
          flex items-center justify-center gap-2
          transition-all duration-200
          ${status.sincronizando
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95'
          }
        `}
      >
        <RefreshCw className={`w-5 h-5 ${status.sincronizando ? 'animate-spin' : ''}`} />
        {status.sincronizando ? 'Sincronizando...' : 'Sincronizar Agora'}
      </button>

      {/* Info adicional */}
      <div className="mt-4 p-3 bg-gray-50 rounded text-xs text-gray-600">
        <p className="font-medium mb-1">ℹ️ Informação:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>A sincronização baixa TODO o conteúdo do AVA</li>
          <li>Seus dados ficam salvos até a próxima sincronização</li>
          <li>Sincronize sempre que houver novas atividades no AVA</li>
        </ul>
      </div>
    </div>
  );
};

export default BotaoSincronizarAVA;


/**
 * VERSÃO COMPACTA (para navbar ou sidebar)
 */
export const BotaoSyncCompacto = () => {
  const [sincronizando, setSincronizando] = useState(false);
  const [ultimaSync, setUltimaSync] = useState(null);

  useEffect(() => {
    const verificarStatus = async () => {
      try {
        const res = await fetch('/api/status_sync');
        const data = await res.json();
        setSincronizando(data.sincronizando);
        setUltimaSync(data.ultima_sync_formatada);
      } catch (error) {
        console.error('Erro ao verificar status:', error);
      }
    };

    verificarStatus();
    const interval = setInterval(verificarStatus, 10000); // 10s
    return () => clearInterval(interval);
  }, []);

  const sincronizar = async () => {
    try {
      await fetch('/api/sincronizar_ava', { method: 'POST' });
      setSincronizando(true);
    } catch (error) {
      console.error('Erro:', error);
    }
  };

  return (
    <div className="relative group">
      <button
        onClick={sincronizar}
        disabled={sincronizando}
        className="p-2 rounded-lg hover:bg-gray-100 transition-colors relative"
        title={ultimaSync ? `Última sync: ${ultimaSync}` : 'Sincronizar com AVA'}
      >
        <RefreshCw
          className={`w-5 h-5 text-gray-600 ${sincronizando ? 'animate-spin' : ''}`}
        />
        {sincronizando && (
          <span className="absolute top-0 right-0 w-2 h-2 bg-blue-600 rounded-full animate-pulse"></span>
        )}
      </button>

      {/* Tooltip */}
      <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2
                      hidden group-hover:block bg-gray-900 text-white text-xs
                      py-1 px-2 rounded whitespace-nowrap z-50">
        {ultimaSync ? `Última sync: ${ultimaSync}` : 'Sincronizar com AVA'}
      </div>
    </div>
  );
};