import { BrowserRouter, Route, Routes } from 'react-router-dom';
import AuthProvider from './auth/AuthProvider.jsx';
import Layout from './components/Layout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
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

            <Route element={<ProtectedRoute />}>
              <Route path='/profile' element={<ProfilePage />} />
              <Route path='/profile/favorites' element={<FavoritesPage />} />
              <Route
                path='/profile/favorites/:recipeId'
                element={<FavoriteRecipePage />}
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
