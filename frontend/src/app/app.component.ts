import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
/** Root application component which serves to render the main shell and allows for authentication-aware navigation. */
export class AppComponent implements OnInit {
  appTitle = 'Voting App';
  isLoggedIn = false;
  isAdmin = false;

  constructor(private authService: AuthService, private router: Router) {}

  ngOnInit(): void {
    this.isLoggedIn = this.authService.isLoggedIn();
    this.isAdmin = this.authService.isAdmin();

    if (this.isLoggedIn) {
      this.authService.whoAmI().subscribe({
        next: () => {
          this.isAdmin = this.authService.isAdmin();
          this.isLoggedIn = true;
        },
        error: () => {
          this.isAdmin = false;
          this.isLoggedIn = false;
        }
      });
    }

    this.authService.currentUser$.subscribe((user) => {
      this.isLoggedIn = !!user || this.authService.isLoggedIn();
      this.isAdmin = this.authService.isAdmin();
    });
  }

  get showAdminLink(): boolean {
    return this.isLoggedIn && this.isAdmin;
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
