import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  IconButton,
  Button,
  Box,
  Tabs,
  Tab,
  InputBase,
  alpha,
  styled,
} from '@mui/material';
import {
  QrCodeScanner as QrIcon,
  Search as SearchIcon,
  Login as LoginIcon,
} from '@mui/icons-material';

// ----- Styled Search Bar -----
const Search = styled('div')(({ theme }) => ({
  position: 'relative',
  borderRadius: theme.shape.borderRadius,
  backgroundColor: alpha(theme.palette.common.white, 0.15),
  '&:hover': {
    backgroundColor: alpha(theme.palette.common.white, 0.25),
  },
  marginRight: theme.spacing(2),
  marginLeft: 0,
  width: 'auto',
  transition: 'width 0.3s ease',
  [theme.breakpoints.up('sm')]: {
    width: 'auto',
  },
}));

const SearchIconWrapper = styled('div')(({ theme }) => ({
  padding: theme.spacing(0, 2),
  height: '100%',
  position: 'absolute',
  pointerEvents: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  zIndex: 1,
}));

const StyledInputBase = styled(InputBase)(({ theme }) => ({
  color: 'inherit',
  width: 0,
  transition: 'width 0.3s ease',
  '& .MuiInputBase-input': {
    padding: theme.spacing(1, 1, 1, 0),
    paddingLeft: `calc(1em + ${theme.spacing(4)})`,
    width: '0',
    transition: 'width 0.3s ease',
    '&:focus': {
      width: '20ch',
    },
  },
  '&.expanded': {
    width: '20ch',
    '& .MuiInputBase-input': {
      width: '20ch',
    },
  },
}));

// ----- Main Component -----
const Navbar = () => {
  const navigate = useNavigate();
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [tabValue, setTabValue] = useState(0);

  const handleSearchClick = () => {
    setSearchExpanded(!searchExpanded);
    if (!searchExpanded) {
      // Focus input after expansion
      setTimeout(() => {
        document.getElementById('search-input')?.focus();
      }, 100);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchValue.trim()) {
      navigate(`/explore?search=${encodeURIComponent(searchValue)}`);
      setSearchExpanded(false);
      setSearchValue('');
    }
  };

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
    const routes = ['/', '/events', '/bookings', '/expenditure'];
    navigate(routes[newValue]);
  };

  return (
    <AppBar position="static" sx={{ bgcolor: '#f57c00' }}> {/* Orange primary */}
      <Toolbar sx={{ flexWrap: 'wrap', gap: 1 }}>
        {/* Left: QR Scan Icon */}
        <IconButton
          edge="start"
          color="inherit"
          aria-label="scan QR"
          onClick={() => navigate('/scan')}
          sx={{ mr: 2 }}
        >
          <QrIcon />
        </IconButton>

        {/* Brand / Logo */}
        <Link to="/" style={{ textDecoration: 'none', color: 'white', flexGrow: 1 }}>
          <Box component="span" sx={{ fontWeight: 'bold', fontSize: '1.2rem' }}>
            E‑Pearl
          </Box>
        </Link>

        {/* Animated Search Bar */}
        <Search sx={{ display: 'flex', alignItems: 'center' }}>
          <SearchIconWrapper onClick={handleSearchClick}>
            <SearchIcon sx={{ color: 'white' }} />
          </SearchIconWrapper>
          <form onSubmit={handleSearchSubmit}>
            <StyledInputBase
              id="search-input"
              placeholder="Search venues…"
              inputProps={{ 'aria-label': 'search' }}
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              className={searchExpanded ? 'expanded' : ''}
            />
          </form>
        </Search>

        {/* Right: Login Button */}
        <Button
          color="inherit"
          startIcon={<LoginIcon />}
          onClick={() => navigate('/login')}
          sx={{ ml: 2 }}
        >
          Login
        </Button>
      </Toolbar>

      {/* Navigation Tabs (below header) */}
      <Box sx={{ bgcolor: '#ef6c00', px: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          textColor="inherit"
          indicatorColor="secondary"
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            '& .MuiTab-root': {
              color: 'rgba(255,255,255,0.7)',
              fontWeight: 'bold',
              '&.Mui-selected': {
                color: 'white',
              },
            },
          }}
        >
          <Tab label="Venues" />
          <Tab label="Events" />
          <Tab label="My Bookings" />
          <Tab label="My Expenditure" />
        </Tabs>
      </Box>
    </AppBar>
  );
};

export default Navbar;