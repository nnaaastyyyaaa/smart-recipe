import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AuthProvider from './auth/AuthProvider.jsx';
import GuestRoute from './components/GuestRoute.jsx';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import LoginPage from './pages/auth/LoginPage.jsx';
import RegisterPage from './pages/auth/RegisterPage.jsx';
import ProductsPage from './pages/generation/ProductsPage.jsx';
import RestrictionsPage from './pages/generation/RestrictionsPage.jsx';
import SuggestionsPage from './pages/generation/SuggestionsPage.jsx';
import HomePage from './pages/home/HomePage.jsx';
import FavoriteRecipePage from './pages/profile/FavoriteRecipePage.jsx';
import FavoritesPage from './pages/profile/FavoritesPage.jsx';
import ProfilePage from './pages/profile/ProfilePage.jsx';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path='/' element={<HomePage />} />

            <Route element={<GuestRoute />}>
              <Route path='/login' element={<LoginPage />} />
              <Route path='/register' element={<RegisterPage />} />
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route path='/profile' element={<ProfilePage />} />
              <Route path='/profile/favorites' element={<FavoritesPage />} />
              <Route
                path='/profile/favorites/:recipeId'
                element={<FavoriteRecipePage />}
              />
              <Route
                path='/generate/:generationId/restrictions'
                element={<RestrictionsPage />}
              />
              <Route
                path='/generate/:generationId/products'
                element={<ProductsPage />}
              />
              <Route
                path='/generate/:generationId/suggestions'
                element={<SuggestionsPage />}
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}