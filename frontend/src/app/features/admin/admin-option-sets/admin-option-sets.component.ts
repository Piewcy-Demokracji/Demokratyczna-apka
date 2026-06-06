import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { TemplateService, Template } from '../../../core/services/template.service';

@Component({
  selector: 'app-admin-option-sets',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-option-sets.component.html',
  styleUrl: './admin-option-sets.component.css'
})
/** Admin page for reviewing and managing published or pending option set templates. */
export class AdminOptionSetsComponent implements OnInit {
  isLoading = true;
  templates: Template[] = [];
  publishedTemplates: Template[] = [];
  notPublishedTemplates: Template[] = [];

  constructor(
    private authService: AuthService,
    private templateService: TemplateService,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/login']);
      return;
    }

    this.authService.whoAmI().subscribe({
      next: (me) => {
        if (!me.is_admin) {
          this.router.navigate(['/profile']);
          return;
        }
        this.loadTemplates();
      },
      error: () => {
        this.router.navigate(['/login']);
      }
    });
  }

  loadTemplates(): void {
    this.isLoading = true;
    this.templateService.getAdminReviewTemplates().subscribe({
      next: (templates) => {
        this.templates = templates;
        this.publishedTemplates = templates.filter(template => template.is_publish === true);
        this.notPublishedTemplates = templates.filter(template => template.is_publish !== true);
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading admin review templates:', error);
        this.isLoading = false;
      }
    });
  }

  openReview(template: Template): void {
    this.router.navigate(['/admin/option-sets', template.id]);
  }

  rejectFromList(template: Template): void {
    this.templateService.rejectFromAdminReview(template.id).subscribe({
      next: () => {
        this.loadTemplates();
      },
      error: (error) => {
        console.error('Error rejecting template from list:', error);
      }
    });
  }

  goProfile(): void {
    this.router.navigate(['/profile']);
  }
}
