import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';

interface LoginRequest {
  username: string;
  password: string;
}

interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
}

interface MeResponse {
  username: string;
  is_admin: boolean;
}

@Injectable({
  providedIn: 'root'
})
/** Service that manages authentication state, token storage, and current user information. */
export class AuthService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/auth';
  private currentUserSubject = new BehaviorSubject<string | null>(this.getStoredUsername());
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {}

  /**
   * Register a new user account.
   *
   * @param username The username for the new account.
   * @param email The email address for the new account.
   * @param password The password for the new account.
   * @returns An observable with the created user response.
   */
  register(username: string, email: string, password: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/register`, {
      username,
      email,
      password
    });
  }

  /**
   * Authenticate a user and store the returned JWT token.
   *
   * @param username The username to log in with.
   * @param password The password to log in with.
   * @returns An observable containing the auth token response.
   */
  login(username: string, password: string): Observable<AuthResponse> {
    const body = { username, password };
    const headers = new HttpHeaders({ 'Content-Type': 'application/json' });

  
    return this.http.post<AuthResponse>('https://demokratyczny-backend.azurewebsites.net/api/auth/login', body, { headers }).pipe(
      tap(response => {
        localStorage.setItem('token', response.access_token);
        localStorage.setItem('username', username);
        localStorage.setItem('is_admin', 'false');
        this.currentUserSubject.next(username);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('is_admin');
    this.currentUserSubject.next(null);
  }

  /**
   * Check whether a user is currently logged in based on stored token presence.
   *
   * @returns True when an authentication token exists, otherwise false.
   */
  isLoggedIn(): boolean {
    return !!localStorage.getItem('token');
  }

  /**
   * Fetch the authenticated user's profile from the backend.
   *
   * @returns An observable containing the current user's username and admin flag.
   */
  whoAmI(): Observable<MeResponse> {
    return this.http.get<MeResponse>(`${this.apiUrl}/me`).pipe(
      tap(me => {
        localStorage.setItem('username', me.username);
        localStorage.setItem('is_admin', String(me.is_admin));
        this.currentUserSubject.next(me.username);
      })
    );
  }

  /**
   * Determine whether the current user has admin privileges.
   *
   * @returns True when the stored admin flag is set, otherwise false.
   */
  isAdmin(): boolean {
    return localStorage.getItem('is_admin') === 'true';
  }

  /**
   * Get the currently stored authentication token.
   *
   * @returns The JWT token string or null if not set.
   */
  getToken(): string | null {
    return localStorage.getItem('token');
  }

  /**
   * Get the currently stored username.
   *
   * @returns The username or null if none is stored.
   */
  getCurrentUsername(): string | null {
    return localStorage.getItem('username');
  }

  private getStoredUsername(): string | null {
    return localStorage.getItem('username');
  }
}
