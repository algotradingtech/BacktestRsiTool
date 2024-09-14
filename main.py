import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from plotly.graph_objs import Indicator


# Classe pour l'interface Streamlit
class BacktestRSIApp:
    def __init__(self):
        self.data = None
        self.bt = None
        self.output = None
        self.setup_ui()

    def setup_ui(self):
        st.title("Backtest RSI simplifié 📊")
        st.markdown("""
        Bienvenue dans cet outil de backtest RSI. Suivez ces étapes pour tester une stratégie de trading simple :
        1. **Choisissez la source de données** : Soit un fichier CSV avec les colonnes standard (Date, Open, High, Low, Close), soit des données de marché à partir de Yahoo Finance.
        2. **Configurez vos paramètres** : Définissez votre capital de départ, levier, risque par trade et les bornes de l'indicateur RSI.
        3. **Exécutez le backtest** : Nous calculerons les performances de votre stratégie sur les données sélectionnées.
        """)
        self.choose_data_source()
        if self.data is not None:
            self.set_parameters()

    def choose_data_source(self):
        data_source = st.radio("Sélectionnez la source de données", ("CSV", "Yahoo Finance"))

        if data_source == "CSV":
            uploaded_file = st.file_uploader("Téléchargez votre fichier CSV")
            if uploaded_file is not None:
                self.data = self.load_csv_data(uploaded_file)

        elif data_source == "Yahoo Finance":
            symbol = st.text_input("Entrez le symbole de l'actif (ex: EURUSD=X)", "EURUSD=X")
            timeframe = st.selectbox("Sélectionnez le timeframe", ["1d", "4h","1h", "15m","5m"])
            self.data = self.load_yahoo_data(symbol, timeframe)

    def load_csv_data(self, uploaded_file):
        try:
            data = pd.read_csv(uploaded_file, parse_dates=True, index_col='Date')
            st.success("Fichier CSV chargé avec succès.")
            st.write(data.tail())
            return data
        except Exception as e:
            st.error(f"Erreur lors du chargement du CSV : {e}")
            return None

    def load_yahoo_data(self, symbol, timeframe):
        try:
            data = yf.download(symbol, period='max', interval=timeframe)
            st.success("Données Yahoo Finance téléchargées avec succès.")
            st.write(data.tail())
            return data
        except Exception as e:
            st.error(f"Erreur lors du téléchargement des données Yahoo Finance : {e}")
            return None

    def set_parameters(self):
        num_candles = len(self.data)
        st.write(f"Nombre de bougies disponibles : {num_candles}")
        self.capital= st.sidebar.number_input("Capital de départ (€)", min_value=1000.0, max_value=10000.0, value=5000.0,step=500.0)
        self.leverage = st.sidebar.number_input("Levier", min_value=1.0, max_value=100.0, value=1.0, step=1.0)
        self.risk_percentage = st.sidebar.number_input("Risque par trade (%)", min_value=0.1, max_value=100.0,value=1.0, step=0.5)
        self.period = st.sidebar.number_input("Période du RSI", min_value=7, max_value=50, value=14, step=1)
        self.upper_bound = st.sidebar.number_input("Borne haute du RSI", min_value=50, max_value=95, value=70, step=5)
        self.lower_bound = st.sidebar.number_input("Borne basse du RSI", min_value=5, max_value=50, value=30, step=5)

        # Ajouter RSI à la DataFrame
        self.data['RSI'] = ta.rsi(self.data['Close'], length=self.period)

        # Bouton pour lancer le backtest
        if st.button("Lancer le backtest"):
            self.run_backtest()

    def run_backtest(self):
        # Configurer et exécuter le backtest
        RSIStrategy.upper_bound = self.upper_bound
        RSIStrategy.lower_bound = self.lower_bound
        RSIStrategy.risk = self.risk_percentage
        RSIStrategy.leverage = self.leverage

        # Supprimer la colonne Date pour éviter les erreurs avec les formats de date
        self.bt = Backtest(self.data.reset_index(drop=True), RSIStrategy, cash=self.capital, commission=0.002, margin=1/self.leverage)
        self.output = self.bt.run()

        # Afficher les résultats du backtest
        st.subheader("Résultats du backtest")
        st.write(self.output)
        profit_total = round((self.output['Equity Final [$]'] - self.capital), 2)

        # Utiliser st.success() ou st.error() en fonction du profit
        if profit_total < 0:
            st.error(f"Profit total : {profit_total} €")
        else:
            st.success(f"Profit total : {profit_total} €")

        # Afficher le graphique de l'équité via bt.plot()
        self.bt.plot()

# Classe pour la stratégie RSI
class RSIStrategy(Strategy):
    upper_bound = 70
    lower_bound = 30
    risk = 1.0

    def init(self):
        def display(indicator):
            return indicator
        self.rsi = self.I(display, self.data.RSI)


    def next(self):
        rsi_t = self.rsi[-1]
        rsi_t_minus_1 = self.rsi[-2]
        # Taille de la position en fonction du capital et du levier
        capital_with_leverage = self.equity * self.leverage
        position_size = capital_with_leverage / self.data.Close[-1]

        # Calcul du stop loss
        stop_loss_long = self.data.Close[-1] - (self.equity * (self.risk / 100)) / position_size
        stop_loss_short = (self.equity * (self.risk / 100)) / position_size + self.data.Close[-1]
        # Fermer la position inverse
        if self.position.is_long and rsi_t_minus_1 > self.upper_bound and rsi_t < self.upper_bound:
            self.position.close()

        if self.position.is_short and rsi_t_minus_1 < self.lower_bound and rsi_t > self.lower_bound:
            self.position.close()

        # Prendre position
        if rsi_t_minus_1 < self.lower_bound and rsi_t > self.lower_bound:
            if not self.position.is_long:
                self.buy(size=int(position_size), sl=stop_loss_long)

        elif rsi_t_minus_1 > self.upper_bound and rsi_t < self.upper_bound:
            if not self.position.is_short:
                self.sell(size=int(position_size), sl=stop_loss_short)

# Lancer l'application
if __name__ == "__main__":
    BacktestRSIApp()



