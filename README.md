<div align="center">

<img src="logo.png" alt="Logo do SCM (SSL Certificate Monitor)" width="380">

# SCM (SSL Certificate Monitor)

**Aplicativo desktop para acompanhar a validade de certificados HTTPS no Windows 11.**

Consulta o certificado, estima a localização do IP conectado e avisa quando um certificado está perto de vencer ou já expirou.

</div>

## Conteúdo

- [Funcionalidades](#funcionalidades)
- [Requisitos](#requisitos)
- [Instalação e execução pelo VS Code](#instalação-e-execução-pelo-vs-code)
- [Como usar](#como-usar)
- [Monitoramento em segundo plano](#monitoramento-em-segundo-plano)
- [Como funcionam os alertas](#como-funcionam-os-alertas)
- [Localização do servidor](#localização-do-servidor)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Limitações e observações de segurança](#limitações-e-observações-de-segurança)
- [Solução de problemas](#solução-de-problemas)

## Funcionalidades

- **Painel visual:** apresenta os domínios monitorados, o prazo restante do certificado, o IP conectado, a data de expiração e a localização estimada.
- **Cadastro de domínios:** aceita tanto `exemplo.com` quanto uma URL completa, como `https://exemplo.com/pagina`.
- **Verificação em segundo plano:** realiza uma varredura ao iniciar e repete a consulta automaticamente a cada **15 minutos**. As consultas de rede acontecem fora da thread gráfica para manter a janela responsiva.
- **Ícones e estados no painel:** mostra se o certificado está dentro do prazo, próximo do vencimento, expirado ou se houve erro na consulta.
- **Alertas de vencimento:** gera um alerta quando faltam **7 dias ou menos** para o vencimento e outro quando identifica um certificado expirado. O mesmo estágio de alerta não é repetido em todas as varreduras.
- **Notificações do sistema:** no Windows, tenta enviar notificações nativas usando Winotify e utiliza Plyer como alternativa quando Winotify falha; Plyer também permite notificações em ambientes compatíveis com macOS e Linux. A exibição final depende das permissões e configurações do sistema operacional.
- **Bandeja do sistema:** utiliza o ícone azul de escudo e cadeado em `icone_bandeja.png`. Fechar a janela normalmente esconde o aplicativo perto do relógio, mantendo a verificação ativa. O menu do ícone oferece opções para abrir o painel, verificar agora e encerrar o aplicativo.
- **Dados persistentes por usuário:** guarda a lista de domínios e o estado dos alertas na pasta de dados do usuário, independente da pasta em que o projeto foi extraído. O `dados.json` antigo é importado automaticamente na primeira execução.
- **Localização com alternativa:** consulta dois serviços públicos de geolocalização em sequência e mantém os resultados temporariamente em cache. Uma falha no primeiro serviço não impede a tentativa pelo segundo.
- **Execução manual:** não há script `iniciar.bat` e o aplicativo não foi configurado para iniciar junto com o Windows. Ele começa somente quando você executa `main.py` pelo VS Code ou pelo Python.

## Requisitos

- Windows 11 recomendado. A interface e as notificações usam bibliotecas multiplataforma, mas a disponibilidade e o comportamento exatos dependem do sistema operacional e de seus serviços de notificação.
- Python **3.10 ou superior**.
- Visual Studio Code.
- Extensão **Python**, publicada pela Microsoft, instalada no VS Code.
- Acesso à internet para consultar os sites HTTPS e os serviços de localização `ipwho.is` e `ipapi.co`.

As bibliotecas necessárias estão listadas em `requirements.txt`. A instalação inclui CustomTkinter, Requests, Cryptography, pystray, Pillow, Plyer e Winotify (no Windows).

## Instalação e execução pelo VS Code

1. Extraia o arquivo ZIP para uma pasta.
2. Abra o VS Code e selecione **Arquivo → Abrir Pasta...**. Escolha a pasta extraída que contém `main.py` e `requirements.txt` (o nome da pasta pode variar conforme o ZIP).
3. Abra o terminal integrado pelo menu **Terminal → Novo Terminal**.
4. Instale as dependências. No Windows, tente:

   ```powershell
   py -m pip install -r requirements.txt
   ```

   Se o comando `py` não existir no computador, use:

   ```powershell
   python -m pip install -r requirements.txt
   ```

5. Abra `main.py` e clique em **Run Python File** no canto superior direito. Como alternativa, abra **Run and Debug**, escolha **SCM (SSL Certificate Monitor) (main.py)** e pressione **F5**.

A instalação das dependências precisa ser feita apenas uma vez para o ambiente Python selecionado. Depois disso, para iniciar o aplicativo basta executar `main.py`. **Não é necessário usar arquivo `.bat`.**

> Dica: se o VS Code pedir para selecionar um interpretador Python, escolha o mesmo Python no qual você instalou as dependências.

## Como usar

1. Inicie o aplicativo executando `main.py`.
2. Digite um domínio, por exemplo `exemplo.com`, ou cole uma URL completa. Clique em **+ Monitorar** ou pressione Enter.
3. O domínio será salvo e a verificação será solicitada. Quando a consulta terminar, o cartão mostrará o prazo do certificado, o IP conectado e a localização estimada.
4. Use **Verificar agora** para solicitar uma nova varredura sem esperar o próximo intervalo automático.
5. Clique no botão `✕` de um cartão para remover aquele domínio da lista.
6. Para fechar a janela sem parar o monitoramento, use o botão de fechar da janela. O aplicativo ficará na bandeja do sistema, perto do relógio do Windows.
7. Para reabrir o painel, clique com o botão direito no ícone da bandeja e selecione **Abrir SCM (SSL Certificate Monitor)**. Para finalizar completamente, escolha **Encerrar**.

## Monitoramento em segundo plano

O monitor começa automaticamente **depois que você executa o aplicativo**. Ele verifica todos os domínios salvos assim que inicia e repete as verificações em intervalos de 15 minutos. O botão **Verificar agora** pede que a próxima varredura aconteça antes desse intervalo.

Fechar a janela não encerra o processo: com a bandeja disponível, a janela é escondida e o monitor continua ativo. Para parar o monitoramento, selecione **Encerrar** no menu da bandeja ou finalize o processo. Desligar o computador também interrompe o programa.

**Importante:** o aplicativo não roda como serviço do Windows, não inicia automaticamente quando o computador liga e não monitora quando o processo está encerrado. Para iniciar o monitoramento, abra o projeto no VS Code e execute `main.py`.

Se a bandeja do sistema não puder ser iniciada, o aplicativo informa o problema no terminal e usa a minimização para a barra de tarefas como alternativa. Nesse caso, não encerre a execução do Python se quiser continuar monitorando.

## Como funcionam os alertas

- **Mais de 30 dias restantes:** estado verde, prazo OK.
- **De 8 a 30 dias restantes:** estado laranja, atenção.
- **De 0 a 7 dias restantes:** estado vermelho e alerta de certificado próximo do vencimento.
- **Certificado expirado:** o domínio fica sinalizado em vermelho no painel e o app envia uma notificação do sistema operacional, quando suportado e permitido.
- **Erro de consulta:** o cartão indica erro de conexão ou de leitura. A falha de uma consulta não deve encerrar o monitoramento dos outros domínios.

O estágio do alerta é registrado nos dados do usuário. Durante o funcionamento normal, a mesma notificação não é repetida a cada varredura se o certificado continua no mesmo estágio. **Ao iniciar o aplicativo, porém, os domínios já salvos são reavaliados e os certificados que continuam próximos do vencimento ou expirados geram um novo aviso.** Isso permite recuperar alertas de sites monitorados mesmo depois de o aplicativo ter sido totalmente encerrado. O estágio só é confirmado no arquivo depois que a biblioteca de notificação aceita o envio; se houver falha, a tentativa fica pendente para uma varredura posterior.

O aplicativo não exibe um pop-up próprio dentro da interface. Ele solicita notificações ao sistema operacional. No Windows, a aparência, a cor e o posicionamento são controlados pelo próprio Windows e não podem ser definidos livremente pelo app.

Para receber as notificações, deixe-as habilitadas em **Configurações do Windows → Sistema → Notificações** e permita notificações para o ambiente de execução. O aplicativo precisa continuar em execução para detectar mudanças e enviar alertas.

## Localização do servidor

O aplicativo consulta o IP que foi efetivamente usado na conexão HTTPS e tenta obter os dados primeiro em `ipwho.is` e, se necessário, em `ipapi.co`. Quando um serviço responde, o painel pode exibir cidade, região, país e organização/provedor. A resposta válida é armazenada em cache por até 24 horas; falhas também são armazenadas por um período curto para evitar consultas excessivas.

A localização é **uma estimativa baseada no IP**, não uma leitura de GPS nem uma medição da posição física exata do equipamento que hospeda o site. Sites com CDN, proxy, balanceamento de carga ou serviços como Cloudflare podem apresentar um IP de infraestrutura intermediária. Se o serviço de geolocalização estiver indisponível, o certificado ainda pode ser verificado, mas os campos de localização podem ficar vazios.

## Estrutura do projeto

```text
SCM (SSL Certificate Monitor)/
├── main.py                    # Interface, painel e rotina do monitor
├── dados.json                 # Dados antigos; importados automaticamente se encontrados
├── requirements.txt            # Dependências Python
├── logo.png                   # Logo principal do projeto
├── icone_bandeja.png          # Ícone da bandeja e das notificações
├── README.md                   # Este guia
├── .vscode/
│   └── launch.json             # Configuração para executar com F5
└── modulos/
    ├── ssl_checker.py          # Consulta SSL, validade, IP e localização
    ├── notificacoes.py        # Notificações do sistema operacional
    └── persistencia.py       # Dados na pasta do usuário e migração do JSON antigo
```

## Limitações e observações de segurança

- **Validade não é uma auditoria TLS completa.** Para ler a data de certificados já vencidos, a consulta extrai o certificado sem validar a cadeia de confiança TLS. Portanto, o estado exibido se refere principalmente à data de expiração e não garante que o certificado seja confiável, que o domínio corresponda ao certificado ou que toda a configuração HTTPS esteja segura.
- **A disponibilidade não é garantida.** Uma falha de DNS, conexão, bloqueio de rede ou limitação de consultas pode impedir uma varredura. O app não prevê se um servidor realmente vai cair; ele monitora a data de validade do certificado.
- **O IP pode variar.** Um domínio pode resolver para endereços diferentes conforme a rede, o DNS, o balanceamento de carga e a infraestrutura do site.
- **Serviços externos de geolocalização.** Para mostrar a localização, o IP conectado é consultado em serviços públicos. Sem internet, com bloqueio de DNS/firewall, limitação de consultas ou falha dos dois serviços, a localização pode não aparecer; nesse caso, o painel exibe um aviso. A localização é aproximada e depende dos dados desses provedores.
- **Notificações do sistema.** O sistema operacional pode ocultar ou agrupar notificações, e políticas de dispositivo podem bloqueá-las. A biblioteca conseguir enviar uma notificação não garante que o sistema a mostre visualmente; permita notificações para o aplicativo/ambiente Python nas configurações do sistema.

## Solução de problemas

### O comando `py` ou `python` não funciona

Verifique se o Python está instalado e disponível no PATH. No VS Code, use **Ctrl+Shift+P → Python: Select Interpreter** e selecione a instalação correta.

### Não foi possível importar uma biblioteca

Abra o terminal integrado na pasta que contém `requirements.txt` e execute novamente:

```powershell
py -m pip install -r requirements.txt
```

Confira se o terminal está usando o mesmo interpretador selecionado no VS Code.

### A localização não aparece

Verifique a conexão com a internet e se o firewall/antivírus permite conexões HTTPS para `ipwho.is` e `ipapi.co`. O app tenta os dois serviços, mas endereços de CDN, proxy e alguns IPs podem não ter localização detalhada. O arquivo `scm.log`, na pasta de dados do usuário, pode ajudar a identificar falhas de consulta.

### A notificação não apareceu

Confira **Configurações do Windows → Sistema → Notificações**, desative temporariamente o modo Não incomodar/Foco e permita notificações para o ambiente de execução. Ao abrir o aplicativo, os sites salvos em estado de alerta são verificados novamente. Se a biblioteca não conseguir enviar a notificação, o painel indica que há uma tentativa pendente e o app tenta novamente em uma varredura posterior. Consulte também `scm.log` na pasta de dados do usuário.

### Onde ficam os dados e o log

No Windows, a lista de domínios e o log ficam em `%APPDATA%\SCM (SSL Certificate Monitor)\dados.json` e `%APPDATA%\SCM (SSL Certificate Monitor)\scm.log`. Em outros sistemas, o app usa a pasta de dados do usuário conforme `XDG_DATA_HOME` ou `~/.local/share/SCM (SSL Certificate Monitor)`. O projeto não precisa de permissão de gravação na pasta em que foi extraído.

### O monitor parou depois de fechar o VS Code

Isso acontece porque o aplicativo é um processo Python iniciado manualmente. Mantenha a execução de `main.py` ativa para que o monitor continue funcionando. O projeto não foi configurado para rodar como serviço nem para iniciar com o Windows.
