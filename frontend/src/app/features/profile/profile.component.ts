import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TemplateService, Template } from '../../core/services/template.service';
import { SessionService } from '../../core/services/session.service';

interface OptionSet {
  id: number;
  name: string;
  optionsCount: number;
  description?: string;
}

@Component({
  selector: 'app-profile',
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
/** Component for the user profile page where the current user can manage option sets and launch sessions. */
export class ProfileComponent implements OnInit {
  username = 'PlaceholderUser';
  isAdmin = false;
  optionSets: OptionSet[] = [];

  get usernameInitial(): string {
    return this.username ? this.username.charAt(0).toUpperCase() : '?';
  }

  constructor(
    private authService: AuthService,
    private templateService: TemplateService,
    private sessionService: SessionService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }

    this.authService.whoAmI().subscribe({
      next: data => {
        this.username = data.username;
        this.isAdmin = data.is_admin;
        this.loadOptionSets();
      },
      error: () => {
        this.username = this.authService.getCurrentUsername() || 'PlaceholderUser';
        this.isAdmin = this.authService.isAdmin();
        this.loadOptionSets();
      }
    });
  }

  loadOptionSets(): void {
    this.templateService.getTemplates('mine').subscribe({
      next: (templates: Template[]) => {
        this.optionSets = templates.map(template => ({
          id: template.id,
          name: template.title,
          optionsCount: template.options.length,
          description: template.description
        }));
      },
      error: (error) => {
        console.error('Error loading option sets:', error);
      }
    });
  }

  editSet(set: OptionSet): void {
    this.router.navigate(['/profile/edit-option-set', set.id]);
  }

  launchSet(set: OptionSet): void {
    this.sessionService.createSession({ template_id: set.id }).subscribe({
      next: response => {
        this.router.navigate(['/session', response.token]);
      },
      error: (error) => {
        console.error('Error creating session:', error);
      }
    });
  }

  deleteSet(set: OptionSet): void {
    if (confirm(`Are you sure you want to delete "${set.name}"?`)) {
      this.templateService.deleteTemplate(set.id).subscribe({
        next: () => {
          this.loadOptionSets();
        },
        error: (error) => {
          console.error('Error deleting option set:', error);
        }
      });
    }
  }

  addOptionSet(): void {
    this.router.navigate(['/profile/create-option-set']);
  }

  goToAdminReview(): void {
    this.router.navigate(['/admin/option-sets']);
  }

  goHome(): void {
    this.router.navigate(['/']);
  }
}
