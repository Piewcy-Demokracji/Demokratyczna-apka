import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { SessionService } from '../../core/services/session.service';
import { TemplateService } from '../../core/services/template.service';

interface OptionSet {
  id: number;
  name: string;
  optionsCount: number;
  description?: string;
}

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
/** Component for the home page showing public option sets, session join features, and quick navigation. */
export class HomeComponent implements OnInit {
  isLoggedIn = false;
  isAdmin = false;
  currentUsername: string | null = null;
  joinCode = '';
  errorMessage: string | null = null;
  publicOptionSets: OptionSet[] = [];

  constructor(
    private authService: AuthService,
    private sessionService: SessionService,
    private templateService: TemplateService,
    private router: Router
  ) {
    this.authService.currentUser$.subscribe(username => {
      this.currentUsername = username;
      this.isLoggedIn = !!username;
      this.isAdmin = this.authService.isAdmin();
    });
  }

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.authService.whoAmI().subscribe({
        next: data => {
          this.isAdmin = data.is_admin;
          this.loadPublicOptionSets();
        },
        error: () => {
          this.isAdmin = this.authService.isAdmin();
          this.loadPublicOptionSets();
        }
      });
    } else {
      this.loadPublicOptionSets();
    }
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/']);
  }

  updateJoinCode(value: string): void {
    this.joinCode = value.toUpperCase();
  }

  enterSession(): void {
    if (!this.joinCode) {
      this.errorMessage = 'Enter your session code.';
      return;
    }

    this.sessionService.joinSession(this.joinCode.trim()).subscribe({
      next: response => {
        this.errorMessage = null;
        this.router.navigate(['/session', response.token]);
      },
      error: () => {
        this.errorMessage = 'Invalid session code.';
        this.joinCode = '';
      }
    });
  }

  loadPublicOptionSets(): void {
    this.templateService.getPublicTemplates().subscribe({
      next: templates => {
        this.publicOptionSets = templates.map(template => ({
          id: template.id,
          name: template.title,
          optionsCount: template.options.length,
          description: template.description
        }));
      },
      error: error => {
        console.error('Error loading public option sets:', error);
      }
    });
  }

  launchSet(set: OptionSet): void {
    if (!this.isLoggedIn) {
      this.router.navigate(['/login']);
      return;
    }

    this.router.navigate(['/session/launch', set.id]);
  }
}
