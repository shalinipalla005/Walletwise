# 💸 Walletwise

A modern, feature-rich expense tracking application built with Streamlit and SQLite. Track personal and group expenses, analyze spending patterns, and manage budgets with an intuitive interface.

## Features

### Personal Finance Management
-  Add, edit, and delete transactions (expenses/income)
-  Dashboard with spending analytics and visualizations
-  Monthly budget tracking (overall and per category)
-  Advanced filtering by date, category, and transaction type
-  Interactive charts and financial insights

### Group Expense Management
-  Split expenses with friends and family
-  Equal or custom amount splitting
-  Track who paid and who owes
-  Settlement tracking and history
-  Group expense dashboard

### Data Visualization
-  Daily/Weekly/Monthly/Yearly trends
-  Category-wise expense breakdown
-  Interactive charts with Plotly
-  Spending pattern analysis
-  Budget utilization tracking

### User Interface
-  Dark/Light theme support
-  Responsive design
-  Interactive dashboards
-  Real-time updates
-  Intuitive navigation

##  Technical Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **Database:** SQLite
- **Authentication:** Passlib (bcrypt)
- **Visualization:** Plotly
- **Data Processing:** Pandas

##  Requirements

```
streamlit==1.37.1
pandas==2.2.2
plotly==5.23.0
passlib[bcrypt]==1.7.4
python-dateutil==2.9.0.post0
```

##  Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/Naveen0030/Expenses_Tracker.git
cd expense-tracker
```

2. Create and activate a virtual environment:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
streamlit run streamlit_app.py
```

The application will automatically create the database file (`expense_tracker.db`) when first run.

##  Usage

### 1. Authentication
- Register a new account with your email
- Log in with your credentials
- Session management handles authentication state

### 2. Adding Transactions
- Click "Add Transaction" in the navigation
- Fill in transaction details (amount, category, date, etc.)
- Choose between expense or income
- Add optional details like payment method and tags

### 3. Group Expenses
- Navigate to "Group Expenses"
- Create new group expenses
- Split amounts equally or custom
- Track and settle payments
- View group expense history

### 4. Reports and Analytics
- View spending trends
- Analyze category-wise expenses
- Track budget utilization
- Export data as needed

### 5. Budget Management
- Set monthly budgets
- Track overall and category-wise budgets
- View budget utilization progress
- Get insights on spending patterns

##  Data Management

- Data is stored locally in SQLite database
- Automatic database creation and schema management
- Support for data import/export
- Secure password hashing

##  Security Features

- Password hashing using bcrypt
- Email format validation
- Input validation and sanitization
- Secure session management

##  Database Schema

The application uses the following main tables:
- `users`: User account information
- `transactions`: Individual financial transactions
- `budgets`: Monthly budget settings
- `group_expenses`: Shared expense records
- `group_expense_shares`: Individual shares in group expenses

##  Contributing

Feel free to:
- Report bugs
- Suggest features
- Submit pull requests


##  Acknowledgments

- Streamlit for the amazing framework
- The Python community for excellent libraries
- Contributors and users of this project

##  Contact

For any queries or suggestions, please open an issue in the GitHub repository.
