/// <reference types="cypress" />
import 'cypress-file-upload';

// Cypress test suite for Customer Chat Widget advanced features
describe('Customer Chat Widget', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('shows unread badge when minimized and new message arrives', () => {
    cy.get('[aria-_label="Minimize chat"]').click();
    cy.window().then((win) => {
      win.dispatchEvent(new Event('focus'));
    });
    cy.get('textarea[aria-_label="Chat input"]').type('Hello{enter}');
    cy.get('[aria-_label="Open chat"] .bg-red-500').should('exist');
  });

  it('shows escalation badge and reports to backend', () => {
    cy.intercept('POST', '**/report_escalation').as('reportEscalation');
    cy.get('textarea[aria-_label="Chat input"]').type('urgent problem{enter}');
    cy.get('[aria-live="assertive"]').contains('URGENT').should('exist');
    cy.wait('@reportEscalation').its('response.statusCode').should('eq', 200);
  });

  it('uploads and displays an image', () => {
    const fileName = 'test-image.png';
    cy.fixture(fileName, 'base64').then((fileContent) => {
      cy.get('_label[for="file-upload"]').then(() => {
        cy.get('input[type="file"]').attachFile({
          fileContent,
          fileName,
          mimeType: 'image/png',
          encoding: 'base64',
        });
      });
    });
    cy.get('img[alt="uploaded"]').should('exist');
  });

  it('can react to a message with a like', () => {
    cy.get('textarea[aria-_label="Chat input"]').type('Hello!{enter}');
    cy.get('button[aria-_label="Like message"]').first().click();
    cy.get('button[aria-_label="Like message"]').first().contains('👍');
  });

  it('shows typing indicator when agent is responding', () => {
    cy.get('textarea[aria-_label="Chat input"]').type('Hi there!{enter}');
    cy.get('.animate-pulse').contains('Agent is responding...').should('exist');
  });
});
