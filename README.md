# 💸 WalletWise - Personal Finance Tracker

A comprehensive personal finance management application built with Streamlit and SQLite. Track your expenses, manage group expenses, set budgets, and gain insights into your spending patterns.

##  Features

###  Personal Finance Management
- **Transaction Logging**: Easy expense and income tracking with categories, payment methods, and tags
- **Smart Dashboard**: Interactive visualizations with daily, weekly, monthly, and yearly trends
- **Budget Management**: Set overall and category-specific budgets with real-time utilization tracking
- **Advanced Analytics**: Detailed insights with pie charts, line graphs, and category breakdowns

###  Group Expense Management
- **Split Expenses**: Create group expenses with equal or custom splits
- **Settlement Tracking**: Track who owes what and settle up easily
- **Balance Overview**: Clear view of your net balance across all groups
- **Payment Methods**: Record settlement methods and transaction references

###  User Management
- **Secure Authentication**: Password hashing and user session management
- **Multi-user Support**: Each user has their own isolated data
- **Profile Management**: Change passwords and manage account settings

###  Reporting & Insights
- **Visual Analytics**: Interactive charts powered by Plotly
- **Export/Import**: CSV export/import functionality for data portability
- **Time-based Analysis**: Filter and analyze data across different time periods
- **Category Insights**: Understand spending patterns by category

##  Technology Stack

- **Backend**: Python, SQLite
- **Frontend**: Streamlit
- **Visualizations**: Plotly Express
- **Data Processing**: Pandas
- **Authentication**: Custom implementation with password hashing

##  Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/shalinipalla005/walletwise.git
   cd walletwise
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run streamlit_app.py
   ```

5. **Access the app**
   Open your browser and navigate to `http://localhost:8501`

## 📋 Requirements

Create a `requirements.txt` file with the following dependencies:

```txt
streamlit>=1.28.0
pandas>=1.5.0
plotly>=5.15.0
sqlite3
hashlib
datetime
typing
re
```

## 🗂️ Project Structure

<<<<<<< HEAD
```
walletwise/
├── streamlit_app.py          # Main application entry point
├── db.py                     # Database operations and schema
├── auth.py                   # Authentication utilities
├── utils/
│   └── session.py           # Session management utilities
├── pages/
│   ├── 1_🧾_Transaction_Log.py    # Transaction logging page
│   ├── 2_📂_View_Transactions.py  # Transaction viewing/editing
│   ├── 3_📈_Reports.py            # Reports and analytics
│   └── 4_👥_Group_Expenses.py     # Group expense management
├── requirements.txt          # Python dependencies
├── README.md                # Project documentation
└── walletwise.db            # SQLite database (created automatically)
=======
1. Clone the repository:
```bash
git clone https://github.com/shalinipalla005/Walletwise.git
cd Walletwise
>>>>>>> e41d37a4914010fbf0b5cbd423872aa6e1318b66
```

##  Usage Guide

### Getting Started
1. **Register**: Create a new account with your name, email, and password
2. **Login**: Sign in with your credentials
3. **Add Transactions**: Start logging your expenses and income
4. **Set Budgets**: Define monthly budgets for better financial planning

### Key Features Walkthrough

####  Adding Transactions
- Use the "Add Transaction" page or the quick-add forms on the Transaction Log page
- Categorize expenses (Food, Rent, Travel, etc.)
- Add payment methods and optional tags for better organization

####  Dashboard Analytics
- View spending trends over different time periods
- Analyze expenses by category with interactive charts
- Monitor budget utilization with progress bars

####  Group Expenses
- Create shared expenses with friends, family, or roommates
- Choose between equal splits or custom amounts
- Track settlements and balance overviews
- Settle up with various payment methods

####  Reports
- Access detailed spending analysis
- Set and track budgets by category
- View utilization percentages and remaining budget

##  Configuration

### Database Setup
The application automatically creates and manages the SQLite database. The database schema includes tables for:
- Users and authentication
- Personal transactions
- Group expenses and shares
- Budget tracking
- Settlement records

### Customization
- **Categories**: Modify default categories in the database
- **Currency**: Currently set to Indian Rupees (₹) - can be modified in the code
- **Date Formats**: Configurable date display formats
- **Theme**: Streamlit's default theme with custom styling

##  Advanced Features

### Import/Export Functionality
- **Export**: Download your transaction data as CSV
- **Import**: Bulk import transactions from CSV files
- **Data Portability**: Easy migration between different systems

### Security Features
- **Password Hashing**: Secure password storage using industry-standard hashing
- **Session Management**: Secure user sessions with proper authentication
- **Data Isolation**: Each user's data is completely separate and secure

##  Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


##  Known Issues & Troubleshooting

<<<<<<< HEAD
### Common Issues
1. **Database Lock Errors**: Restart the application if you encounter SQLite lock errors
2. **Import Errors**: Ensure CSV files have the correct column format (date, amount, type)
3. **Session Timeouts**: Re-login if you experience unexpected logouts

### Support
If you encounter any issues:
1. Check the console for error messages
2. Ensure all dependencies are installed correctly
3. Verify Python version compatibility
4. Create an issue on GitHub with detailed error information

## 🌟 Future Enhancements

- [ ] Mobile-responsive design improvements
- [ ] Integration with bank APIs for automatic transaction import
- [ ] Advanced budgeting features (yearly budgets, savings goals)
- [ ] Expense prediction using machine learning
- [ ] Multi-currency support
- [ ] Receipt image upload and OCR processing
- [ ] Email notifications for budget alerts
- [ ] Data backup and cloud storage integration

---

**Made using Python and Streamlit**

*WalletWise - Take control of your finances, one transaction at a time.*
=======
- Streamlit for the amazing framework
- The Python community for excellent libraries
- Contributors and users of this project
>>>>>>> e41d37a4914010fbf0b5cbd423872aa6e1318b66
