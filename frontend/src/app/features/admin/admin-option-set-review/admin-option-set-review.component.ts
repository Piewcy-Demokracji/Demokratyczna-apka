import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { TemplateService, Template } from '../../../core/services/template.service';

@Component({
  selector: 'app-admin-option-set-review',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './admin-option-set-review.component.html',
  styleUrl: './admin-option-set-review.component.css'
})
export class AdminOptionSetReviewComponent implements OnInit {
  template: Template | null = null;
  isLoading = true;
  isSubmitting = false;

  constructor(
    private authService: AuthService,
    private templateService: TemplateService,
    private route: ActivatedRoute,
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

        const idParam = this.route.snapshot.paramMap.get('id');
        const id = idParam ? Number(idParam) : NaN;
        if (!id) {
          this.router.navigate(['/admin/option-sets']);
          return;
        }

        this.loadTemplate(id);
      },
      error: () => {
        this.router.navigate(['/login']);
      }
    });
  }

  loadTemplate(id: number): void {
    this.isLoading = true;
    this.templateService.getAdminReviewTemplate(id).subscribe({
      next: (template) => {
        this.template = template;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading template for admin review:', error);
        this.isLoading = false;
        this.router.navigate(['/admin/option-sets']);
      }
    });
  }

  publish(): void {
    if (!this.template || this.isSubmitting) {
      return;
    }

    this.isSubmitting = true;
    this.templateService.publishFromAdminReview(this.template.id).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.router.navigate(['/admin/option-sets']);
      },
      error: (error) => {
        console.error('Error publishing template:', error);
        this.isSubmitting = false;
      }
    });
  }

  reject(): void {
    if (!this.template || this.isSubmitting) {
      return;
    }

    this.isSubmitting = true;
    this.templateService.rejectFromAdminReview(this.template.id).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.router.navigate(['/admin/option-sets']);
      },
      error: (error) => {
        console.error('Error rejecting template:', error);
        this.isSubmitting = false;
      }
    });
  }

  goBack(): void {
    this.router.navigate(['/admin/option-sets']);
  }
}
